from __future__ import annotations

import json
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..database import sessions_collection, users_collection
from ..dependencies import get_current_user
from ..services.agents import call_progress_evaluator

router = APIRouter(prefix="/placement", tags=["placement"])

QUESTIONS = [
    "Hola. Como te llamas? (Hello, what is your name?)",
    "De donde eres? (Where are you from?)",
    "Que haces normalmente en tu dia? (What do you usually do in your day?)",
    "Que hiciste ayer? (What did you do yesterday?)",
    "Que planes tienes para manana? (What plans do you have for tomorrow?)",
    "Describe tu ciudad favorita. (Describe your favorite city.)",
    "Habla de un problema que resolviste. (Talk about a problem you solved.)",
    "Cuentame un recuerdo importante. (Tell me an important memory.)",
]


class PlacementStartResponse(BaseModel):
    session_id: str
    question: str
    index: int


class PlacementAnswerRequest(BaseModel):
    session_id: str
    answer: str
    index: int


class PlacementFinishRequest(BaseModel):
    session_id: str
    cefr_level: str | None = None
    reasoning: str | None = None


@router.get("/start", response_model=PlacementStartResponse)
async def start(user=Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    result = await sessions_collection().insert_one(
        {
            "user_id": user["_id"],
            "session_type": "placement",
            "scenario": None,
            "messages": [],
            "xp_earned": 0,
            "duration_seconds": 0,
            "grammar_errors_count": 0,
            "vocabulary_added_count": 0,
            "started_at": now,
            "ended_at": None,
        }
    )
    return {"session_id": str(result.inserted_id), "question": QUESTIONS[0], "index": 0}


@router.post("/respond")
async def respond(payload: PlacementAnswerRequest, user=Depends(get_current_user)):
    session = await sessions_collection().find_one({"_id": ObjectId(payload.session_id)})
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    message = {
        "role": "user",
        "content": payload.answer,
        "timestamp": datetime.now(timezone.utc),
        "errors": [],
        "new_vocabulary": [],
    }
    await sessions_collection().update_one({"_id": session["_id"]}, {"$push": {"messages": message}})

    next_index = payload.index + 1
    if next_index >= len(QUESTIONS):
        return {"done": True}
    return {"question": QUESTIONS[next_index], "index": next_index}


@router.post("/finish")
async def finish(payload: PlacementFinishRequest, user=Depends(get_current_user)):
    session = await sessions_collection().find_one({"_id": ObjectId(payload.session_id)})
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    transcript = [
        {"role": msg.get("role", "user"), "content": msg.get("content", "")}
        for msg in session.get("messages", [])
    ]
    evaluator_prompt = {
        "role": "user",
        "content": json.dumps(
            {
                "task": "placement_evaluation",
                "conversation": transcript,
                "return_schema": {"cefr_level": "A1", "reasoning": "brief explanation"},
            }
        ),
    }
    result = await call_progress_evaluator([evaluator_prompt], user)
    cefr_level = result.get("cefr_level") or payload.cefr_level or "A1"
    reasoning = result.get("reasoning") or payload.reasoning or ""

    await users_collection().update_one(
        {"_id": user["_id"]},
        {"$set": {"cefr_level": cefr_level, "onboarding_complete": True, "updated_at": datetime.now(timezone.utc)}},
    )
    await sessions_collection().update_one(
        {"_id": ObjectId(payload.session_id)},
        {"$set": {"ended_at": datetime.now(timezone.utc), "xp_earned": 100}},
    )
    return {"cefr_level": cefr_level, "reasoning": reasoning}
