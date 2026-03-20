from __future__ import annotations

from datetime import datetime, timezone
from random import sample
from uuid import uuid4
import unicodedata

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import func, select

from ..database import get_session
from ..dependencies import get_current_user
from ..models.extra import Story
from ..models.session import Session
from ..models.user import User
from ..models.vocabulary import VocabularyItem
from ..services.agents import call_story_narrator
from ..services.notifications import push_notification

router = APIRouter(prefix="/bonus", tags=["bonus"])


class StoryCompleteRequest(BaseModel):
    answers: list[str] | None = None


class SpeedRoundSubmitRequest(BaseModel):
    score: int = 0
    total: int = 0


class ListeningSubmitRequest(BaseModel):
    text: str | None = None
    answer: str | None = None


class VocabSubmitRequest(BaseModel):
    correct_ids: list[int] | None = None
    answers: list[dict] | None = None


class ReadingSubmitRequest(BaseModel):
    answers: list[dict] | None = None


class PodcastSubmitRequest(BaseModel):
    summary: str


class CultureReadRequest(BaseModel):
    accepted: bool = True


_reading_cache: dict[str, dict] = {}
_podcast_cache: dict[str, dict] = {}
_culture_cache: dict[str, dict] = {}

CEFR_ORDER = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}


def _cefr_at_least(user_level: str | None, required: str) -> bool:
    current = CEFR_ORDER.get((user_level or "A1").upper(), 1)
    target = CEFR_ORDER.get(required.upper(), 1)
    return current >= target


def _normalize_text(value: str | None) -> str:
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.split())


def _levenshtein(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)

    previous = list(range(len(right) + 1))
    for i, left_char in enumerate(left, start=1):
        current = [i]
        for j, right_char in enumerate(right, start=1):
            current.append(
                min(
                    current[j - 1] + 1,
                    previous[j] + 1,
                    previous[j - 1] + (left_char != right_char),
                )
            )
        previous = current
    return previous[-1]


async def _ensure_stories(session: AsyncSession, user: User) -> None:
    existing_stmt = select(func.count()).select_from(Story).where(Story.user_id == user.id)
    existing_count = (await session.execute(existing_stmt)).scalar() or 0
    if existing_count >= 3:
        return

    prompt = {
        "role": "user",
        "content": (
            "Create a short story JSON: {title, story, questions:[{q,a}]}. "
            f"Language: {user.target_language or 'spanish'}. CEFR: {user.cefr_level}."
        ),
    }
    for _ in range(3 - existing_count):
        data = await call_story_narrator([prompt], user.model_dump())
        story_id = uuid4().hex
        content = {
            "story": data.get("story", "Historia corta."),
            "questions": data.get("questions", []),
        }
        session.add(
            Story(
                story_id=story_id,
                user_id=user.id,
                language=user.target_language or "spanish",
                title=data.get("title", "Story"),
                content=content,
                read=False,
                created_at=datetime.utcnow(),
            )
        )
    await session.commit()


@router.get("/stories")
async def list_stories(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    await _ensure_stories(session, user)
    stmt = select(Story).where(Story.user_id == user.id).order_by(Story.created_at.desc())
    items = (await session.execute(stmt)).scalars().all()
    payload = []
    for item in items:
        data = item.model_dump()
        data["_id"] = item.id
        payload.append(data)
    return {"items": payload}


@router.post("/stories/{story_id}/complete")
async def complete_story(
    story_id: str,
    payload: StoryCompleteRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Story).where(Story.story_id == story_id, Story.user_id == user.id)
    story = (await session.execute(stmt)).scalar_one_or_none()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    story.read = True
    session.add(story)

    now = datetime.utcnow()
    session.add(
        Session(
            user_id=user.id,
            session_type="story",
            messages=[],
            exercises=[],
            xp_earned=50,
            started_at=now,
            ended_at=now,
        )
    )
    user.xp += 50
    user.weekly_xp += 50
    user.total_xp += 50
    user.total_words_learned += 3
    session.add(user)
    await session.commit()
    return {"xp": 50}


@router.get("/speed-round/start")
async def speed_round_start(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    stmt = select(VocabularyItem).where(VocabularyItem.user_id == user.id).limit(30)
    cards = (await session.execute(stmt)).scalars().all()
    pool = cards if len(cards) > 0 else []
    questions = []
    for card in pool[:10]:
        distractors = [item.translation for item in pool if item.id != card.id][:3]
        options = [card.translation, *distractors][:4]
        if len(options) < 4:
            options.extend(["option_1", "option_2", "option_3"])
            options = options[:4]
        questions.append({"id": card.id, "word": card.word, "correct": card.translation, "options": options})
    return {"round_id": uuid4().hex, "duration_seconds": 30, "questions": questions}


@router.post("/speed-round/complete")
async def speed_round_complete(
    payload: SpeedRoundSubmitRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    score = payload.score or payload.total or 0
    earned_xp = min(100, score * 2)
    now = datetime.utcnow()
    session.add(
        Session(
            user_id=user.id,
            session_type="speed_round",
            xp_earned=earned_xp,
            summary={"score": score, "total": payload.total},
            started_at=now,
            ended_at=now,
        )
    )
    user.xp += earned_xp
    user.weekly_xp += earned_xp
    user.total_xp += earned_xp
    session.add(user)
    await session.commit()
    return {"xp": earned_xp}


@router.get("/listening/{item_id}")
async def listening_item(item_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    stmt = (
        select(VocabularyItem)
        .where(VocabularyItem.user_id == user.id)
        .order_by(VocabularyItem.next_review, VocabularyItem.created_at.desc())
        .limit(1)
    )
    vocab = (await session.execute(stmt)).scalars().first()
    if vocab:
        audio_text = vocab.context_sentence or f"{vocab.word} means {vocab.translation}"
        hint = f"Focus on the word '{vocab.word}'."
        focus = vocab.word
    else:
        audio_text = "Hola, me llamo Sofia y vivo en Madrid."
        hint = "Listen for the proper name and the city."
        focus = "introductions"
    return {
        "id": item_id,
        "prompt": "Listen and type what you hear",
        "audio_text": audio_text,
        "correct_text": audio_text,
        "hint": hint,
        "focus": focus,
        "xp_reward": 25,
    }


@router.post("/listening/{item_id}/submit")
async def listening_submit(
    item_id: str,
    payload: ListeningSubmitRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    submitted = (payload.text or payload.answer or "").strip()
    item = await listening_item(item_id, user, session)
    expected = _normalize_text(item["correct_text"])
    actual = _normalize_text(submitted)
    distance = _levenshtein(actual, expected) if actual and expected else 99
    accepted_with_typo = distance == 1 and len(expected) > 4
    almost_correct = distance <= 2 and not accepted_with_typo and actual != expected
    is_correct = actual == expected or accepted_with_typo
    earned = 25 if is_correct else 12 if almost_correct else 5
    now = datetime.utcnow()
    session.add(
        Session(
            user_id=user.id,
            session_type="listening",
            xp_earned=earned,
            summary={
                "item_id": item_id,
                "user_text": submitted,
                "is_correct": is_correct,
                "accepted_with_typo": accepted_with_typo,
                "almost_correct": almost_correct,
                "correct_text": item["correct_text"],
            },
            started_at=now,
            ended_at=now,
        )
    )
    user.xp += earned
    user.weekly_xp += earned
    user.total_xp += earned
    session.add(user)
    await session.commit()
    return {
        "correct": is_correct,
        "accepted_with_typo": accepted_with_typo,
        "almost_correct": almost_correct,
        "correct_text": item["correct_text"],
        "hint": None if is_correct else item["hint"],
        "xp": earned,
    }


@router.get("/vocab-challenge/today")
async def vocab_today(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    stmt = select(VocabularyItem).where(VocabularyItem.user_id == user.id).limit(20)
    cards = (await session.execute(stmt)).scalars().all()
    questions = []
    for card in cards[:5]:
        questions.append({"id": card.id, "word": card.word, "translation": card.translation})
    return {"challenge_id": uuid4().hex, "time_limit": 60, "questions": questions}


@router.post("/vocab-challenge/submit")
async def vocab_submit(
    payload: VocabSubmitRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    correct_ids = payload.correct_ids or []
    if not correct_ids and payload.answers:
        correct_ids = [int(item["id"]) for item in payload.answers if item.get("correct")]

    if correct_ids:
        stmt = select(VocabularyItem).where(VocabularyItem.id.in_(correct_ids), VocabularyItem.user_id == user.id)
        cards = (await session.execute(stmt)).scalars().all()
        for card in cards:
            card.status = "known"
            card.next_review = datetime.utcnow()
            session.add(card)

    earned = min(30, len(correct_ids) * 6)
    now = datetime.utcnow()
    session.add(
        Session(
            user_id=user.id,
            session_type="vocab_challenge",
            xp_earned=earned,
            summary={"score": len(correct_ids)},
            started_at=now,
            ended_at=now,
        )
    )
    user.xp += earned
    user.weekly_xp += earned
    user.total_xp += earned
    user.gems += 5 if len(correct_ids) >= 5 else 2
    session.add(user)
    await session.commit()

    if len(correct_ids) >= 5:
        await push_notification(session, user.id, "Daily challenge complete", "You aced today's vocab challenge", "challenge")
    return {"xp": earned, "gems": 5 if len(correct_ids) >= 5 else 2}


@router.get("/reading/start")
async def reading_start(user: User = Depends(get_current_user)):
    if not _cefr_at_least(user.cefr_level, "B1"):
        raise HTTPException(status_code=403, detail="Reading comprehension unlocks at B1.")

    item_id = uuid4().hex
    prompt = {
        "role": "user",
        "content": (
            "Generate JSON: {title, article, questions:[{id, question, options:[...], answer}]}. "
            f"Target language: {user.target_language or 'spanish'}. CEFR: {user.cefr_level}. "
            f"Topics: {', '.join(user.goals or ['daily life'])}."
        ),
    }
    data = await call_story_narrator([prompt], user.model_dump())
    questions = data.get("questions", []) if isinstance(data, dict) else []
    article = data.get("article") if isinstance(data, dict) else None
    if not article:
        article = (
            "La ciudad cambio mucho este ano. Nuevas rutas de transporte ayudaron a los estudiantes "
            "a llegar mas rapido a la universidad. Muchos tambien empezaron a trabajar en proyectos "
            "ecologicos con sus vecinos para reducir residuos y mejorar los parques locales."
        )
    if not questions:
        questions = [
            {"id": 1, "question": "Que mejoro en la ciudad?", "options": ["Transporte", "Clima", "Precios", "Turismo"], "answer": "Transporte"},
            {"id": 2, "question": "Quienes participaron en proyectos ecologicos?", "options": ["Vecinos y estudiantes", "Solo turistas", "Medicos", "Empresas"], "answer": "Vecinos y estudiantes"},
            {"id": 3, "question": "Cual fue un objetivo principal?", "options": ["Reducir residuos", "Aumentar trafico", "Cerrar parques", "Viajar"], "answer": "Reducir residuos"},
            {"id": 4, "question": "Que paso con los parques?", "options": ["Mejoraron", "Cerraron", "Desaparecieron", "No cambiaron"], "answer": "Mejoraron"},
            {"id": 5, "question": "El texto habla principalmente de:", "options": ["Mejoras comunitarias", "Comida", "Historia antigua", "Deportes"], "answer": "Mejoras comunitarias"},
        ]

    _reading_cache[item_id] = {"questions": questions, "created_at": datetime.utcnow()}
    return {
        "id": item_id,
        "title": (data.get("title") if isinstance(data, dict) else None) or "Reading Challenge",
        "article": article,
        "questions": questions,
        "xp_reward": 70,
    }


@router.post("/reading/{item_id}/submit")
async def reading_submit(
    item_id: str,
    payload: ReadingSubmitRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    cached = _reading_cache.get(item_id)
    if not cached:
        raise HTTPException(status_code=404, detail="Reading challenge not found")

    answers = payload.answers or []
    answer_map = {str(a.get("id")): a.get("answer") for a in answers}
    score = 0
    for q in cached["questions"]:
        if answer_map.get(str(q.get("id"))) == q.get("answer"):
            score += 1

    earned = 70 if score >= 4 else 35 if score >= 2 else 15
    now = datetime.utcnow()
    session.add(
        Session(
            user_id=user.id,
            session_type="reading",
            xp_earned=earned,
            accuracy_percent=int((score / max(len(cached["questions"]), 1)) * 100),
            summary={"score": score, "total": len(cached["questions"]), "item_id": item_id},
            started_at=now,
            ended_at=now,
        )
    )
    user.xp += earned
    user.weekly_xp += earned
    user.total_xp += earned
    user.total_words_learned += 5
    session.add(user)
    await session.commit()
    return {"score": score, "total": len(cached["questions"]), "xp": earned}


@router.get("/podcast/start")
async def podcast_start(user: User = Depends(get_current_user)):
    if not _cefr_at_least(user.cefr_level, "B2"):
        raise HTTPException(status_code=403, detail="Podcast mode unlocks at B2.")

    item_id = uuid4().hex
    prompt = {
        "role": "user",
        "content": (
            "Generate JSON: {title, script, key_points:[...], prompt}. "
            f"Target language: {user.target_language or 'spanish'}. CEFR: {user.cefr_level}. "
            "The script should feel like two hosts discussing one topic for 3-5 minutes."
        ),
    }
    data = await call_story_narrator([prompt], user.model_dump())
    script = data.get("script") if isinstance(data, dict) else None
    if not script:
        script = (
            "Host A: Hoy hablamos sobre habitos de estudio.\n"
            "Host B: Si, especialmente como mantener la constancia sin cansarse.\n"
            "Host A: Una idea util es dividir el estudio en bloques cortos."
        )
    prompt_text = (data.get("prompt") if isinstance(data, dict) else None) or "Write 3 sentences summarizing the podcast."
    _podcast_cache[item_id] = {"created_at": datetime.utcnow(), "script": script}
    return {
        "id": item_id,
        "title": (data.get("title") if isinstance(data, dict) else None) or "Podcast Episode",
        "script": script,
        "key_points": (data.get("key_points") if isinstance(data, dict) else None) or [],
        "summary_prompt": prompt_text,
        "xp_reward": 80,
    }


@router.post("/podcast/{item_id}/submit")
async def podcast_submit(
    item_id: str,
    payload: PodcastSubmitRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    cached = _podcast_cache.get(item_id)
    if not cached:
        raise HTTPException(status_code=404, detail="Podcast episode not found")

    summary = payload.summary.strip()
    if len(summary) < 15:
        raise HTTPException(status_code=400, detail="Please write at least 3 short sentences.")

    earned = 80
    now = datetime.utcnow()
    session.add(
        Session(
            user_id=user.id,
            session_type="podcast",
            xp_earned=earned,
            summary={"item_id": item_id, "summary": summary},
            started_at=now,
            ended_at=now,
        )
    )
    user.xp += earned
    user.weekly_xp += earned
    user.total_xp += earned
    session.add(user)
    await session.commit()
    return {"xp": earned}


@router.get("/culture-notes")
async def culture_notes(user: User = Depends(get_current_user)):
    note_id = f"{(user.target_language or 'spanish')}-food-travel-greetings"
    cached = _culture_cache.get(note_id)
    if cached:
        return cached

    prompt = {
        "role": "user",
        "content": (
            "Generate JSON: {title, paragraphs:[p1,p2,p3], skill_tags:[...]}. "
            f"Target language culture: {user.target_language or 'spanish'}. "
            "Focus on food, travel, and greetings differences."
        ),
    }
    data = await call_story_narrator([prompt], user.model_dump())
    payload = {
        "id": note_id,
        "title": (data.get("title") if isinstance(data, dict) else None) or "Culture Note",
        "paragraphs": (data.get("paragraphs") if isinstance(data, dict) else None)
        or [
            "En muchos paises hispanohablantes, la comida es una actividad social larga y compartida.",
            "Al viajar, escuchar expresiones locales ayuda a crear conversaciones mas naturales y amables.",
            "Los saludos cambian por region; usar el tono correcto muestra respeto cultural.",
        ],
        "skill_tags": (data.get("skill_tags") if isinstance(data, dict) else None) or ["food", "travel", "greetings"],
        "xp_reward": 25,
    }
    _culture_cache[note_id] = payload
    return payload


@router.post("/culture-notes/{note_id}/read")
async def culture_note_read(
    note_id: str,
    payload: CultureReadRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if not payload.accepted:
        return {"xp": 0}

    earned = 25
    now = datetime.utcnow()
    session.add(
        Session(
            user_id=user.id,
            session_type="culture_note",
            xp_earned=earned,
            summary={"note_id": note_id},
            started_at=now,
            ended_at=now,
        )
    )
    user.xp += earned
    user.weekly_xp += earned
    user.total_xp += earned
    session.add(user)
    await session.commit()
    return {"xp": earned}
