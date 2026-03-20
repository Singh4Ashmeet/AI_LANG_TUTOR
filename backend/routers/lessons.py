from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
import unicodedata
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import select

from ..config import settings
from ..database import get_session
from ..dependencies import get_current_user
from ..models.extra import GrammarStat
from ..models.session import Session
from ..models.user import User
from ..models.vocabulary import VocabularyItem
from ..services.achievements import check_and_award_achievements
from ..services.agents import call_feedback_coach, call_lesson_architect
from ..services.notifications import push_notification

router = APIRouter(prefix="/lessons", tags=["lessons"])


class LessonStartRequest(BaseModel):
    skill_id: int
    lesson_index: int = 0


class ExerciseAnswerRequest(BaseModel):
    session_id: int
    exercise_index: int
    user_answer: Any
    time_ms: int | None = None


class LessonCompleteRequest(BaseModel):
    session_id: int


def _normalize(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip().lower()
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {str(k).strip().lower(): _normalize(v) for k, v in value.items()}
    return value


def _normalize_text(value: Any) -> str:
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
            insert_cost = current[j - 1] + 1
            delete_cost = previous[j] + 1
            replace_cost = previous[j - 1] + (left_char != right_char)
            current.append(min(insert_cost, delete_cost, replace_cost))
        previous = current
    return previous[-1]


def _grade_answer(exercise: dict, answer: Any) -> dict[str, Any]:
    ex_type = int(exercise.get("type", 0))
    correct_answer = exercise.get("correct_answer")

    if ex_type in {1, 10}:
        return {"is_correct": True, "almost_correct": False, "accepted_with_typo": False}
    if ex_type == 7:
        spoken = isinstance(answer, str) and len(answer.strip()) > 0
        return {"is_correct": spoken, "almost_correct": False, "accepted_with_typo": False}
    if ex_type in {6, 8}:
        exact = _normalize(answer) == _normalize(correct_answer)
        return {"is_correct": exact, "almost_correct": False, "accepted_with_typo": False}

    expected = _normalize_text(correct_answer)
    actual = _normalize_text(answer)
    accepted_answers = [_normalize_text(item) for item in (exercise.get("accepted_answers") or []) if item]

    if actual == expected or (actual and actual in accepted_answers):
        return {"is_correct": True, "almost_correct": False, "accepted_with_typo": False}

    distance = _levenshtein(actual, expected) if actual and expected else 99
    max_typo_distance = 1
    if distance <= max_typo_distance:
        return {
            "is_correct": True,
            "almost_correct": True,
            "accepted_with_typo": True,
            "correction_type": "spelling",
        }

    near_miss = distance <= max_typo_distance + 1
    return {
        "is_correct": False,
        "almost_correct": near_miss,
        "accepted_with_typo": False,
        "correction_type": "spelling" if near_miss else None,
    }


def _default_lesson(skill_id: int) -> dict:
    return {
        "skill_id": skill_id,
        "lesson_focus": "Greetings and identity",
        "teaching_objective": "Learn a phrase, recognize it, build it, then use it in context.",
        "focus_reason": "This lesson starts with high-frequency basics so you can understand before producing.",
        "guidebook": [
            {
                "title": "Start with meaning",
                "explanation": "First learn what the phrase means before you have to produce it.",
                "examples": [{"target": "Hola", "native": "Hello"}],
            },
            {
                "title": "Notice the pattern",
                "explanation": "Short sentence patterns repeat across the lesson.",
                "examples": [{"target": "Yo soy estudiante", "native": "I am a student"}],
            },
            {
                "title": "Build before typing",
                "explanation": "Word bank and matching tasks help you prepare for harder questions.",
                "examples": [{"target": "Estoy feliz", "native": "I am happy"}],
            },
        ],
        "exercises": [
            {
                "type": 1,
                "stage": "teach",
                "instruction": "Read and notice the meaning",
                "content": "Hola means Hello. This is a new phrase, so you are learning it before being tested.",
                "correct_answer": "hola",
                "explanation": "New language should be introduced before production.",
                "hint": "Say it out loud once before continuing.",
                "safe_exercise": True,
            },
            {
                "type": 1,
                "stage": "teach",
                "instruction": "Study the pattern",
                "content": "Yo soy estudiante = I am a student.",
                "correct_answer": "yo soy estudiante",
                "explanation": "This shows the full sentence before any fill-in-the-blank task.",
                "hint": "Notice how yo pairs with soy.",
                "safe_exercise": True,
            },
            {
                "type": 2,
                "stage": "recognize",
                "instruction": "Tap the best answer",
                "content": "Pick the correct translation for 'Good morning'",
                "choices": ["Buenas noches", "Buenos dias", "Hasta luego"],
                "correct_answer": "Buenos dias",
                "explanation": "Buenos dias is used for good morning.",
            },
            {
                "type": 6,
                "stage": "recognize",
                "instruction": "Match the pairs",
                "content": "Match each word with its meaning",
                "choices": [{"left": "agua", "right": "water"}, {"left": "casa", "right": "house"}],
                "correct_answer": {"agua": "water", "casa": "house"},
                "explanation": "Matching reinforces vocabulary before harder production work.",
                "hint": "Match the easiest pair first.",
            },
            {
                "type": 8,
                "stage": "build",
                "instruction": "Build the sentence",
                "content": "Arrange the words into a sentence",
                "choices": ["yo", "estudio", "espanol"],
                "correct_answer": ["yo", "estudio", "espanol"],
                "explanation": "Sentence building helps you feel the word order.",
                "hint": "Start with the subject.",
            },
            {
                "type": 3,
                "stage": "guided",
                "instruction": "Fill in the missing word",
                "content": "Yo ___ estudiante.",
                "correct_answer": "soy",
                "accepted_answers": ["Soy"],
                "grammar_rule": "ser-present",
                "explanation": "Use soy with yo in the present tense.",
                "hint": "Think of the present-tense form of ser for yo.",
                "answer_mode": "spelling",
            },
            {
                "type": 9,
                "stage": "listen",
                "instruction": "Listen and spell what you hear",
                "content": "Type the phrase exactly after listening.",
                "audio_text": "Me llamo Sofia",
                "correct_answer": "Me llamo Sofia",
                "explanation": "Listening review helps connect sound and meaning.",
                "hint": "Listen for the double-l sound in llamo.",
                "answer_mode": "dictation",
            },
            {
                "type": 4,
                "stage": "produce",
                "instruction": "Translate into the target language",
                "content": "I am happy.",
                "correct_answer": "Estoy feliz",
                "accepted_answers": ["Estoy muy feliz"],
                "grammar_rule": "estar-adjective",
                "explanation": "Use estoy for temporary feelings like happy.",
                "hint": "Use estar here, not ser.",
                "answer_mode": "typing",
            },
            {
                "type": 7,
                "stage": "speak",
                "instruction": "Say it aloud",
                "content": "Me gusta aprender idiomas",
                "correct_answer": "voice_recorded",
                "explanation": "Speaking comes after you've seen and understood the pattern.",
                "safe_exercise": True,
            },
            {
                "type": 10,
                "stage": "coach",
                "instruction": "Respond naturally",
                "content": "Mini conversation: Someone says 'Hola, me llamo Ana.' Reply naturally.",
                "correct_answer": "any",
                "explanation": "The final step uses the language in a tiny real-world context.",
                "hint": "A short greeting and your name is enough.",
                "safe_exercise": True,
            },
        ],
    }


async def _lesson_personalization(session: AsyncSession, user: User) -> dict[str, Any]:
    grammar_stmt = (
        select(GrammarStat)
        .where(GrammarStat.user_id == user.id, GrammarStat.language == (user.target_language or "spanish"))
        .order_by(GrammarStat.errors.desc())
        .limit(3)
    )
    vocab_stmt = (
        select(VocabularyItem)
        .where(VocabularyItem.user_id == user.id, VocabularyItem.status.in_(["new", "learning"]))
        .limit(5)
    )
    sessions_stmt = (
        select(Session)
        .where(Session.user_id == user.id, Session.session_type == "lesson")
        .order_by(Session.started_at.desc())
        .limit(5)
    )

    grammar_items = (await session.execute(grammar_stmt)).scalars().all()
    vocab_items = (await session.execute(vocab_stmt)).scalars().all()
    recent_sessions = (await session.execute(sessions_stmt)).scalars().all()

    recent_rules = []
    recent_prompts: list[str] = []
    for lesson_session in recent_sessions:
        for exercise in lesson_session.exercises or []:
            if exercise.get("is_correct") is False:
                if exercise.get("grammar_rule"):
                    recent_rules.append(str(exercise.get("grammar_rule")))
                if exercise.get("content"):
                    recent_prompts.append(str(exercise.get("content")))

    top_recent_prompts = [item for item, _ in Counter(recent_prompts).most_common(3)]
    return {
        "weak_grammar": [item.rule for item in grammar_items],
        "review_vocabulary": [item.word for item in vocab_items],
        "recent_mistakes": top_recent_prompts,
        "recent_rules": [item for item, _ in Counter(recent_rules).most_common(3)],
    }


async def _generate_lesson(skill_id: int, user: User, session: AsyncSession) -> dict:
    personalization = await _lesson_personalization(session, user)
    prompt = {
        "role": "user",
        "content": (
            "Generate a Duolingo-style lesson JSON with exactly 10 exercises using types 1-10. "
            "The sequence must teach before testing: first teach/introduction, then recognition, then sentence building, then guided production, then open production. "
            "Include at least one spelling-sensitive or dictation-style exercise and make the lesson feel supportive, not punishing. "
            "Use the learner's weak grammar and review vocabulary when relevant. "
            "Return JSON only with this shape: "
            "{skill_id, lesson_focus, teaching_objective, focus_reason, guidebook:[{title, explanation, examples:[{target,native}]}], "
            "exercises:[{type, stage, instruction, content, choices, correct_answer, accepted_answers, explanation, grammar_rule, audio_text, safe_exercise, hint, answer_mode}]}. "
            f"Skill id: {skill_id}. Target language: {user.target_language or 'spanish'}. Native language: {user.native_language or 'english'}. "
            f"Weak grammar: {', '.join(personalization['weak_grammar']) or 'none'}. "
            f"Review vocabulary: {', '.join(personalization['review_vocabulary']) or 'none'}. "
            f"Recent mistakes: {' | '.join(personalization['recent_mistakes']) or 'none'}."
        ),
    }
    try:
        result = await call_lesson_architect([prompt], user.model_dump())
        if isinstance(result, dict) and isinstance(result.get("exercises"), list) and len(result["exercises"]) == 10:
            result.setdefault(
                "focus_reason",
                "This lesson leans into your recent weak spots while still introducing the target pattern gently.",
            )
            return result
    except Exception:
        pass
    return _default_lesson(skill_id)


@router.post("/start")
async def start_lesson(
    payload: LessonStartRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    lesson = await _generate_lesson(payload.skill_id, user, session)
    exercises = lesson.get("exercises", [])
    now = datetime.utcnow()
    db_session = Session(
        user_id=user.id,
        session_type="lesson",
        skill_id=str(payload.skill_id),
        lesson_index=payload.lesson_index,
        messages=[],
        summary={
            "lesson_focus": lesson.get("lesson_focus"),
            "teaching_objective": lesson.get("teaching_objective"),
            "focus_reason": lesson.get("focus_reason"),
            "guidebook": lesson.get("guidebook", []),
        },
        exercises=[
            {
                "type": item.get("type"),
                "stage": item.get("stage"),
                "instruction": item.get("instruction"),
                "content": item.get("content") or item.get("prompt"),
                "choices": item.get("choices"),
                "correct_answer": item.get("correct_answer"),
                "explanation": item.get("explanation"),
                "grammar_rule": item.get("grammar_rule"),
                "audio_text": item.get("audio_text"),
                "safe_exercise": bool(item.get("safe_exercise", False)),
                "hint": item.get("hint"),
                "answer_mode": item.get("answer_mode"),
                "accepted_answers": item.get("accepted_answers") or [],
                "user_answer": None,
                "is_correct": None,
                "time_ms": None,
            }
            for item in exercises
        ],
        xp_earned=0,
        accuracy_percent=0,
        hearts_lost=0,
        duration_seconds=0,
        started_at=now,
    )
    session.add(db_session)
    await session.commit()
    await session.refresh(db_session)
    return {"session_id": db_session.id, "exercises": db_session.exercises, "lesson_meta": db_session.summary or {}}


@router.get("/exercises/cached")
async def cached_exercises(
    session_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Session).where(Session.id == session_id, Session.user_id == user.id)
    db_session = (await session.execute(stmt)).scalar_one_or_none()
    if not db_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return {"exercises": db_session.exercises, "lesson_meta": db_session.summary or {}}


@router.post("/exercise/answer")
async def submit_answer(
    payload: ExerciseAnswerRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Session).where(Session.id == payload.session_id, Session.user_id == user.id)
    db_session = (await session.execute(stmt)).scalar_one_or_none()
    if not db_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    exercises = list(db_session.exercises or [])
    if payload.exercise_index < 0 or payload.exercise_index >= len(exercises):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid exercise index")

    exercise = exercises[payload.exercise_index]
    grade = _grade_answer(exercise, payload.user_answer)
    is_correct = bool(grade["is_correct"])
    ex_type = int(exercise.get("type", 0))

    exercise["user_answer"] = payload.user_answer
    exercise["is_correct"] = is_correct
    exercise["time_ms"] = payload.time_ms
    exercises[payload.exercise_index] = exercise
    db_session.exercises = exercises
    flag_modified(db_session, "exercises")

    if not is_correct and ex_type not in {1, 10} and not exercise.get("safe_exercise", False):
        user.hearts = max(0, int(user.hearts) - 1)
        db_session.hearts_lost = int(db_session.hearts_lost or 0) + 1

    now = datetime.utcnow()
    grammar_rule = exercise.get("grammar_rule")
    if grammar_rule:
        grammar_stmt = select(GrammarStat).where(
            GrammarStat.user_id == user.id,
            GrammarStat.rule == grammar_rule,
            GrammarStat.language == (user.target_language or "spanish"),
        )
        grammar_stat = (await session.execute(grammar_stmt)).scalar_one_or_none()
        if not grammar_stat:
            grammar_stat = GrammarStat(
                user_id=user.id,
                rule=grammar_rule,
                language=(user.target_language or "spanish"),
                errors=0,
                attempts=0,
                mastery=0.0,
                last_error_at=now,
            )
        grammar_stat.attempts += 1
        if not is_correct:
            grammar_stat.errors += 1
            grammar_stat.last_error_at = now
        correct_attempts = max(grammar_stat.attempts - grammar_stat.errors, 0)
        grammar_stat.mastery = round(correct_attempts / grammar_stat.attempts, 2) if grammar_stat.attempts else 0.0
        session.add(grammar_stat)

    user.updated_at = datetime.utcnow()
    session.add(user)
    session.add(db_session)
    await session.commit()

    grammar_tip = None
    if not is_correct and ex_type in {3, 4, 5} and exercise.get("grammar_rule"):
        grammar_tip = f"Review rule: {exercise.get('grammar_rule')}"

    encouragement = "Nice work. You are ready for the next step."
    if grade.get("accepted_with_typo"):
        encouragement = "Nice catch. That was accepted, but there was a small spelling slip."
    elif not is_correct and grade.get("almost_correct"):
        encouragement = "Very close. You were near the correct spelling or wording."
    elif not is_correct:
        encouragement = "That's okay. Learn from the correction and keep going."

    return {
        "is_correct": is_correct,
        "almost_correct": bool(grade.get("almost_correct")),
        "accepted_with_typo": bool(grade.get("accepted_with_typo")),
        "correct_answer": exercise.get("correct_answer"),
        "hearts_remaining": user.hearts,
        "explanation": exercise.get("explanation"),
        "grammar_tip": grammar_tip,
        "hint": None if is_correct else exercise.get("hint"),
        "encouragement": encouragement,
    }


@router.post("/complete")
async def complete_lesson(
    payload: LessonCompleteRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Session).where(Session.id == payload.session_id, Session.user_id == user.id)
    db_session = (await session.execute(stmt)).scalar_one_or_none()
    if not db_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    exercises = list(db_session.exercises or [])
    total = len(exercises)
    correct = len([item for item in exercises if item.get("is_correct") is True])
    accuracy = int((correct / total) * 100) if total else 0
    earned = correct * 10
    duration_seconds = int((datetime.utcnow() - db_session.started_at).total_seconds())

    user.xp += earned
    user.weekly_xp += earned
    user.total_xp += earned
    user.total_lessons_complete += 1
    user.total_minutes_practiced += max(1, int(duration_seconds / 60))
    user.last_session_date = datetime.utcnow()

    skill_id = str(db_session.skill_id or "")
    crown_levels = dict(user.crown_levels or {})
    if skill_id:
        crown_levels[skill_id] = min(5, int(crown_levels.get(skill_id, 0)) + 1)
    user.crown_levels = crown_levels

    gems_earned = 0
    if accuracy == 100:
        gems_earned += 5
    today = datetime.utcnow().date()
    if user.total_minutes_practiced >= user.daily_goal_minutes:
        gems_earned += 3
    if user.streak in {7, 30, 100}:
        gems_earned += {7: 10, 30: 30, 100: 50}[user.streak]
    user.gems += gems_earned

    tip_prompt = {
        "role": "user",
        "content": f"accuracy={accuracy}, errors={total - correct}, lesson_skill={skill_id}",
    }
    try:
        coach_tip = await call_feedback_coach([tip_prompt], user.model_dump())
    except Exception:
        coach_tip = "Great consistency. Repeat one tricky sentence out loud three times."

    db_session.ended_at = datetime.utcnow()
    db_session.xp_earned = earned
    db_session.accuracy_percent = accuracy
    db_session.duration_seconds = duration_seconds
    db_session.coach_tip = coach_tip

    session.add(user)
    session.add(db_session)
    await session.commit()

    newly_earned = await check_and_award_achievements(session, user.id)
    if newly_earned:
        await push_notification(
            session,
            user.id,
            "New achievement unlocked",
            f"You earned {newly_earned[0].title}",
            "achievement",
        )
    if gems_earned > 0:
        await push_notification(session, user.id, "Gems earned", f"You earned {gems_earned} gems", "reward")

    return {
        "earned": earned,
        "accuracy_percent": accuracy,
        "total_xp": user.xp,
        "gems_earned": gems_earned,
        "coach_tip": coach_tip,
        "new_achievements": [ach.achievement_id for ach in newly_earned],
        "crown_level": crown_levels.get(skill_id, 0) if skill_id else 0,
    }

