from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from ..database import word_of_day_collection, vocabulary_collection
from ..dependencies import get_current_user
from ..services.agents import call_lesson_architect

router = APIRouter(prefix="/word-of-day", tags=["word_of_day"])


def _pair(user: dict) -> str:
    return f"{user.get('native_language', 'en')}-{user.get('target_language', 'es')}"


@router.get("")
async def get_word(user=Depends(get_current_user)):
    today = datetime.now(timezone.utc).date()
    pair = _pair(user)
    existing = await word_of_day_collection().find_one({"date": today, "language_pair": pair})
    if existing:
        existing["_id"] = str(existing["_id"])
        return existing

    prompt = {
        "role": "user",
        "content": (
            "Generate a Word of the Day JSON: {word, translation, part_of_speech, example_sentence, example_translation}. "
            f"Language pair: {pair}."
        ),
    }
    result = await call_lesson_architect([prompt], user)
    if not isinstance(result, dict):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Word of day generation failed")
    doc = {
        "date": today,
        "language_pair": pair,
        "word": result.get("word"),
        "translation": result.get("translation"),
        "part_of_speech": result.get("part_of_speech"),
        "example_sentence": result.get("example_sentence"),
        "example_translation": result.get("example_translation"),
        "audio_cached": False,
    }
    inserted = await word_of_day_collection().insert_one(doc)
    doc["_id"] = str(inserted.inserted_id)
    return doc


@router.post("/add-to-deck")
async def add_to_deck(user=Depends(get_current_user)):
    word = await get_word(user)
    existing = await vocabulary_collection().find_one({"user_id": user["_id"], "word": word.get("word")})
    if existing:
        return {"added": False}
    await vocabulary_collection().insert_one(
        {
            "user_id": user["_id"],
            "word": word.get("word"),
            "translation": word.get("translation"),
            "language": user.get("target_language"),
            "status": "new",
            "ease_factor": 2.5,
            "interval_days": 1,
            "repetitions": 0,
            "next_review": datetime.now(timezone.utc),
            "last_seen": None,
            "times_seen": 0,
            "times_correct": 0,
            "context_sentence": word.get("example_sentence"),
            "source_session_id": None,
            "source_skill": None,
            "created_at": datetime.now(timezone.utc),
        }
    )
    return {"added": True}
