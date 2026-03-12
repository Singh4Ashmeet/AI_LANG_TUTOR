from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..database import grammar_stats_collection, sessions_collection, users_collection, vocabulary_collection
from ..dependencies import get_current_user
from ..services.learner import award_xp, update_streak
from ..services.agents import call_error_analyst, call_feedback_coach, call_roleplay_engine, call_scenario_creator

router = APIRouter(prefix="/roleplay", tags=["roleplay"])

SCENARIOS = [
    {
        "id": "restaurant",
        "name": "Restaurant",
        "difficulty": "A1",
        "description": "Order food, ask questions, and pay the bill.",
        "skills": ["ordering", "polite requests", "numbers"],
        "ai_role": "Waiter",
        "opening": "Bienvenido. Tiene una reservacion?",
    },
    {
        "id": "airport",
        "name": "Airport",
        "difficulty": "A2",
        "description": "Check in and handle a flight issue.",
        "skills": ["travel", "problem solving", "polite requests"],
        "ai_role": "Check-in agent",
        "opening": "Buenos dias. Puede mostrar su pasaporte?",
    },
    {
        "id": "job_interview",
        "name": "Job Interview",
        "difficulty": "B1",
        "description": "Answer professional questions and discuss experience.",
        "skills": ["career", "self introduction", "past tense"],
        "ai_role": "Interviewer",
        "opening": "Hola. Puede contarme sobre su experiencia reciente?",
    },
    {
        "id": "doctor",
        "name": "Doctor Visit",
        "difficulty": "B1",
        "description": "Describe symptoms and understand advice.",
        "skills": ["health", "describing symptoms", "listening"],
        "ai_role": "Doctor",
        "opening": "Hola. Que le duele hoy?",
    },
    {
        "id": "market",
        "name": "Street Market",
        "difficulty": "A2",
        "description": "Browse, negotiate, and buy something.",
        "skills": ["shopping", "numbers", "bargaining"],
        "ai_role": "Vendor",
        "opening": "Buenos dias. Busca algo especial?",
    },
    {
        "id": "first_date",
        "name": "First Date",
        "difficulty": "B2",
        "description": "Casual conversation about opinions and interests.",
        "skills": ["opinions", "humor", "small talk"],
        "ai_role": "Date",
        "opening": "Hola. Como estuvo tu dia?",
    },
    {
        "id": "hotel",
        "name": "Hotel",
        "difficulty": "A2",
        "description": "Check in and handle a room issue.",
        "skills": ["travel", "requests", "polite tone"],
        "ai_role": "Receptionist",
        "opening": "Bienvenido al hotel. Tiene una reserva?",
    },
    {
        "id": "phone_call",
        "name": "Phone Call",
        "difficulty": "B2",
        "description": "Communicate clearly without visual cues.",
        "skills": ["clarification", "listening", "repetition"],
        "ai_role": "Caller",
        "opening": "Hola, soy Alex. Me escucha bien?",
    },
]


class RoleplayNewRequest(BaseModel):
    scenario_id: str


class RoleplayChatRequest(BaseModel):
    session_id: str
    message: str


class RoleplayCustomRequest(BaseModel):
    prompt: str


@router.get("/scenarios")
async def list_scenarios():
    return SCENARIOS


@router.post("/new")
async def start_roleplay(payload: RoleplayNewRequest, user=Depends(get_current_user)):
    scenario = next((s for s in SCENARIOS if s["id"] == payload.scenario_id), None)
    if not scenario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")

    now = datetime.now(timezone.utc)
    result = await sessions_collection().insert_one(
        {
            "user_id": user["_id"],
            "session_type": "roleplay",
            "scenario": scenario["id"],
            "messages": [
                {
                    "role": "assistant",
                    "content": scenario["opening"],
                    "timestamp": now,
                    "errors": [],
                    "new_vocabulary": [],
                }
            ],
            "xp_earned": 0,
            "duration_seconds": 0,
            "grammar_errors_count": 0,
            "vocabulary_added_count": 0,
            "started_at": now,
            "ended_at": None,
        }
    )
    return {"session_id": str(result.inserted_id), "opening": scenario["opening"]}


@router.post("")
async def roleplay_chat(payload: RoleplayChatRequest, user=Depends(get_current_user)):
    session = await sessions_collection().find_one({"_id": ObjectId(payload.session_id)})
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    analysis = await call_error_analyst([{"role": "user", "content": payload.message}], user)
    errors = analysis.get("errors", [])
    new_vocab = analysis.get("new_vocabulary", [])

    now = datetime.now(timezone.utc)
    for error in errors:
        rule = error.get("rule") or "unknown"
        await grammar_stats_collection().update_one(
            {"user_id": user["_id"], "rule": rule, "language": user.get("target_language")},
            {"$inc": {"errors": 1, "attempts": 1}, "$set": {"last_error_at": now}},
            upsert=True,
        )
    for word in new_vocab:
        existing = await vocabulary_collection().find_one(
            {"user_id": user["_id"], "word": word, "language": user.get("target_language")}
        )
        if existing:
            await vocabulary_collection().update_one(
                {"_id": existing["_id"]},
                {"$inc": {"times_seen": 1}, "$set": {"last_seen": now}},
            )
            continue
        await vocabulary_collection().insert_one(
            {
                "user_id": user["_id"],
                "word": word,
                "translation": "",
                "language": user.get("target_language"),
                "status": "new",
                "ease_factor": 2.5,
                "interval_days": 1,
                "repetitions": 0,
                "next_review": now,
                "last_seen": now,
                "times_seen": 1,
                "times_correct": 0,
                "context_sentence": payload.message,
                "source_session_id": None,
                "source_skill": None,
                "created_at": now,
            }
        )

    user_message = {
        "role": "user",
        "content": payload.message,
        "timestamp": datetime.now(timezone.utc),
        "errors": errors,
        "new_vocabulary": new_vocab,
    }
    await sessions_collection().update_one({"_id": session["_id"]}, {"$push": {"messages": user_message}})

    scenario = next((s for s in SCENARIOS if s["id"] == session.get("scenario")), None)
    role_context = {
        **user,
        "scenario": scenario["description"] if scenario else session.get("scenario"),
        "role": scenario["ai_role"] if scenario else "NPC",
    }
    reply = await call_roleplay_engine([{"role": "user", "content": payload.message}], role_context)

    assistant_message = {
        "role": "assistant",
        "content": reply,
        "timestamp": datetime.now(timezone.utc),
        "errors": [],
        "new_vocabulary": [],
    }
    await sessions_collection().update_one({"_id": session["_id"]}, {"$push": {"messages": assistant_message}})
    return {"reply": reply, "corrections": errors, "new_words": new_vocab}


@router.post("/end/{session_id}")
async def end_roleplay(session_id: str, user=Depends(get_current_user)):
    session = await sessions_collection().find_one({"_id": ObjectId(session_id)})
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    end_time = datetime.now(timezone.utc)
    duration = int((end_time - session["started_at"]).total_seconds())
    await sessions_collection().update_one(
        {"_id": session["_id"]},
        {"$set": {"ended_at": end_time, "duration_seconds": duration}},
    )

    updated_user = await users_collection().find_one({"_id": user["_id"]})
    updated_user = update_streak(updated_user)
    earned, leveled_up, new_level = award_xp(updated_user, base=80)
    updated_user["updated_at"] = datetime.now(timezone.utc)
    await users_collection().update_one({"_id": user["_id"]}, {"$set": updated_user})
    summary_prompt = {
        "role": "user",
        "content": json.dumps(
            {
                "session_type": "roleplay",
                "messages": session.get("messages", []),
            }
        ),
    }
    coach_tip = await call_feedback_coach([summary_prompt], user)
    await sessions_collection().update_one(
        {"_id": session["_id"]},
        {"$set": {"xp_earned": earned, "coach_tip": coach_tip}},
    )

    return {
        "earned": earned,
        "total": updated_user.get("xp", 0),
        "streak": updated_user.get("streak", 0),
        "leveled_up": leveled_up,
        "cefr_level": new_level,
        "coach_tip": coach_tip,
    }


@router.post("/custom")
async def custom_scenario(payload: RoleplayCustomRequest, user=Depends(get_current_user)):
    scenario = await call_scenario_creator(
        [{"role": "user", "content": payload.prompt}],
        user,
    )
    if not scenario:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Scenario creation failed")

    now = datetime.now(timezone.utc)
    scenario_id = f"custom_{uuid4().hex}"
    result = await sessions_collection().insert_one(
        {
            "user_id": user["_id"],
            "session_type": "roleplay",
            "scenario": scenario_id,
            "custom_scenario": scenario,
            "messages": [
                {
                    "role": "assistant",
                    "content": scenario.get("opening_line_in_target_language", ""),
                    "timestamp": now,
                    "errors": [],
                    "new_vocabulary": [],
                }
            ],
            "xp_earned": 0,
            "duration_seconds": 0,
            "grammar_errors_count": 0,
            "vocabulary_added_count": 0,
            "started_at": now,
            "ended_at": None,
        }
    )
    return {
        "session_id": str(result.inserted_id),
        "scenario": scenario,
        "opening": scenario.get("opening_line_in_target_language", ""),
    }
