from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..config import settings
from ..database import sessions_collection, users_collection
from ..dependencies import get_current_user
from ..services.agents import call_lesson_architect
from ..services.learner import update_streak

router = APIRouter(prefix="/lessons", tags=["lessons"])


class LessonStartRequest(BaseModel):
    skill_id: int
    lesson_index: int | None = None


class ExerciseAnswerRequest(BaseModel):
    session_id: str
    exercise_index: int
    user_answer: str | list | dict
    time_ms: int | None = None


class LessonCompleteRequest(BaseModel):
    session_id: str


def _normalize(value):
    if isinstance(value, str):
        return value.strip().lower()
    if isinstance(value, list):
        return [str(item).strip().lower() for item in value]
    if isinstance(value, dict):
        return {str(k).strip().lower(): _normalize(v) for k, v in value.items()}
    return value


def _is_correct(user_answer, correct_answer) -> bool:
    return _normalize(user_answer) == _normalize(correct_answer)


async def _generate_lesson(skill_id: int, user: dict) -> dict:
    prompt = {
        "role": "user",
        "content": (
            "Generate a lesson JSON with exactly 10 exercises (types 1-10). "
            "Return JSON: {skill_id, exercises:[{type, prompt, content, choices, correct_answer, "
            "explanation, audio_text}]} for the target language. "
            f"Skill id: {skill_id}."
        ),
    }
    result = await call_lesson_architect([prompt], user)
    if not isinstance(result, dict):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Lesson generation failed")
    return result


@router.post("/start")
async def start_lesson(payload: LessonStartRequest, user=Depends(get_current_user)):
    lesson = await _generate_lesson(payload.skill_id, user)
    now = datetime.now(timezone.utc)
    exercises = lesson.get("exercises", [])
    session_doc = {
        "user_id": user["_id"],
        "session_type": "lesson",
        "skill_id": str(payload.skill_id),
        "lesson_index": payload.lesson_index or 0,
        "messages": [],
        "exercises": [
            {
                "type": item.get("type"),
                "content": item.get("content") or item.get("prompt"),
                "choices": item.get("choices"),
                "correct_answer": item.get("correct_answer"),
                "explanation": item.get("explanation"),
                "audio_text": item.get("audio_text"),
                "user_answer": None,
                "is_correct": None,
                "time_ms": None,
            }
            for item in exercises
        ],
        "xp_earned": 0,
        "accuracy_percent": 0,
        "hearts_lost": 0,
        "duration_seconds": 0,
        "started_at": now,
        "ended_at": None,
        "hearts_start": user.get("hearts", settings.max_hearts),
        "hearts_remaining": user.get("hearts", settings.max_hearts),
    }
    result = await sessions_collection().insert_one(session_doc)
    return {"session_id": str(result.inserted_id), "exercises": session_doc["exercises"]}


@router.post("/exercise/answer")
async def submit_answer(payload: ExerciseAnswerRequest, user=Depends(get_current_user)):
    session = await sessions_collection().find_one({"_id": ObjectId(payload.session_id), "user_id": user["_id"]})
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    exercises = session.get("exercises", [])
    if payload.exercise_index < 0 or payload.exercise_index >= len(exercises):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid exercise index")

    exercise = exercises[payload.exercise_index]
    ex_type = int(exercise.get("type", 0))
    correct_answer = exercise.get("correct_answer")
    is_correct = True if ex_type in {1, 10} else _is_correct(payload.user_answer, correct_answer)

    exercise["user_answer"] = payload.user_answer
    exercise["is_correct"] = is_correct
    exercise["time_ms"] = payload.time_ms

    hearts_remaining = session.get("hearts_remaining", user.get("hearts", settings.max_hearts))
    hearts_lost = session.get("hearts_lost", 0)
    if not is_correct and ex_type not in {1, 10}:
        hearts_remaining = max(0, hearts_remaining - 1)
        hearts_lost += 1
        await users_collection().update_one({"_id": user["_id"]}, {"$set": {"hearts": hearts_remaining}})

    exercises[payload.exercise_index] = exercise
    await sessions_collection().update_one(
        {"_id": session["_id"]},
        {"$set": {"exercises": exercises, "hearts_remaining": hearts_remaining, "hearts_lost": hearts_lost}},
    )

    return {
        "is_correct": is_correct,
        "correct_answer": correct_answer,
        "hearts_remaining": hearts_remaining,
        "explanation": exercise.get("explanation"),
    }


@router.get("/exercises/cached")
async def cached_exercises(session_id: str, user=Depends(get_current_user)):
    session = await sessions_collection().find_one({"_id": ObjectId(session_id), "user_id": user["_id"]})
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return {"exercises": session.get("exercises", [])}


@router.post("/complete")
async def complete_lesson(payload: LessonCompleteRequest, user=Depends(get_current_user)):
    session = await sessions_collection().find_one({"_id": ObjectId(payload.session_id), "user_id": user["_id"]})
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    exercises = session.get("exercises", [])
    total = len(exercises)
    correct = len([ex for ex in exercises if ex.get("is_correct")])
    accuracy = int((correct / total) * 100) if total else 0
    earned = correct * 10
    duration_seconds = int((datetime.now(timezone.utc) - session.get("started_at")).total_seconds())

    updated_user = await users_collection().find_one({"_id": user["_id"]})
    updated_user = update_streak(updated_user)
    updated_user["xp"] = int(updated_user.get("xp", 0)) + earned
    updated_user["weekly_xp"] = int(updated_user.get("weekly_xp", 0)) + earned
    updated_user["total_xp"] = int(updated_user.get("total_xp", 0)) + earned
    updated_user["total_lessons_complete"] = int(updated_user.get("total_lessons_complete", 0)) + 1
    updated_user["total_minutes_practiced"] = int(updated_user.get("total_minutes_practiced", 0)) + max(1, int(duration_seconds / 60))
    updated_user["updated_at"] = datetime.now(timezone.utc)

    await users_collection().update_one({"_id": user["_id"]}, {"$set": updated_user})
    await sessions_collection().update_one(
        {"_id": session["_id"]},
        {
            "$set": {
                "ended_at": datetime.now(timezone.utc),
                "xp_earned": earned,
                "accuracy_percent": accuracy,
                "duration_seconds": duration_seconds,
            }
        },
    )

    return {"earned": earned, "accuracy_percent": accuracy, "total_xp": updated_user.get("xp", 0)}
