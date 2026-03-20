from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..database import get_session
from ..dependencies import get_current_user
from ..models.extra import WordOfDay
from ..models.user import User
from ..models.vocabulary import VocabularyItem
from ..services.agents import call_lesson_architect

router = APIRouter(prefix="/word-of-day", tags=["word_of_day"])


def _pair(user: User) -> str:
    return f"{(user.native_language or 'english')[:2]}-{(user.target_language or 'spanish')[:2]}"


@router.get("")
async def get_word(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    today = datetime.utcnow().date()
    day_start = datetime(today.year, today.month, today.day)
    pair = _pair(user)

    stmt = select(WordOfDay).where(WordOfDay.date == day_start, WordOfDay.language_pair == pair)
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing:
        return existing.model_dump()

    prompt = {
        "role": "user",
        "content": (
            "Generate JSON: {word, translation, part_of_speech, example_sentence, example_translation}. "
            f"Language pair: {pair}."
        ),
    }
    data = await call_lesson_architect([prompt], user.model_dump())
    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail="Word of day generation failed")

    item = WordOfDay(
        date=day_start,
        language_pair=pair,
        word=data.get("word", "hola"),
        translation=data.get("translation", "hello"),
        part_of_speech=data.get("part_of_speech"),
        example_sentence=data.get("example_sentence"),
        example_translation=data.get("example_translation"),
        audio_cached=False,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item.model_dump()


@router.post("/add-to-deck")
async def add_to_deck(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    word_data = await get_word(user, session)
    existing = (
        await session.execute(
            select(VocabularyItem).where(VocabularyItem.user_id == user.id, VocabularyItem.word == word_data["word"])
        )
    ).scalar_one_or_none()
    if existing:
        return {"added": False}

    now = datetime.utcnow()
    item = VocabularyItem(
        user_id=user.id,
        word=word_data["word"],
        translation=word_data["translation"],
        language=user.target_language or "spanish",
        status="new",
        next_review=now,
        last_seen=now,
        context_sentence=word_data.get("example_sentence"),
        created_at=now,
    )
    session.add(item)
    user.total_words_learned += 1
    session.add(user)
    await session.commit()
    return {"added": True}

