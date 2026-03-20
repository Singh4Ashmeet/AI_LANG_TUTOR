from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import desc, func, select

from ..models.extra import Achievement, UserAchievement
from ..models.session import Session
from ..models.user import User
from ..models.vocabulary import VocabularyItem


ACHIEVEMENTS_DATA = [
    {"achievement_id": "first-lesson", "title": "First Lesson", "description": "Complete any lesson", "icon": "first_lesson", "xp_reward": 10, "condition_type": "lessons", "condition_value": 1, "rarity": "common"},
    {"achievement_id": "first-streak", "title": "First Streak", "description": "Reach a 3-day streak", "icon": "first_streak", "xp_reward": 15, "condition_type": "streak", "condition_value": 3, "rarity": "common"},
    {"achievement_id": "word-collector", "title": "Word Collector", "description": "Add 10 vocabulary words", "icon": "word_collector", "xp_reward": 10, "condition_type": "words", "condition_value": 10, "rarity": "common"},
    {"achievement_id": "quick-learner", "title": "Quick Learner", "description": "Complete 5 lessons in one day", "icon": "quick_learner", "xp_reward": 20, "condition_type": "custom", "condition_value": 5, "rarity": "common"},
    {"achievement_id": "week-warrior", "title": "Week Warrior", "description": "Reach a 7-day streak", "icon": "week_warrior", "xp_reward": 25, "condition_type": "streak", "condition_value": 7, "rarity": "rare"},
    {"achievement_id": "half-century", "title": "Half Century", "description": "Complete 50 lessons", "icon": "half_century", "xp_reward": 40, "condition_type": "lessons", "condition_value": 50, "rarity": "rare"},
    {"achievement_id": "vocabulary-champion", "title": "Vocabulary Champion", "description": "Master 100 words", "icon": "vocab_champion", "xp_reward": 50, "condition_type": "words_mastered", "condition_value": 100, "rarity": "rare"},
    {"achievement_id": "month-master", "title": "Month Master", "description": "Reach a 30-day streak", "icon": "month_master", "xp_reward": 80, "condition_type": "streak", "condition_value": 30, "rarity": "epic"},
    {"achievement_id": "century-streak", "title": "Century Streak", "description": "Reach a 100-day streak", "icon": "century_streak", "xp_reward": 150, "condition_type": "streak", "condition_value": 100, "rarity": "legendary"},
]


async def seed_achievements(session: AsyncSession) -> None:
    for data in ACHIEVEMENTS_DATA:
        statement = select(Achievement).where(Achievement.achievement_id == data["achievement_id"])
        existing = (await session.execute(statement)).scalar_one_or_none()
        if existing:
            continue
        session.add(Achievement(**data))
    await session.commit()


async def _has_perfect_week(session: AsyncSession, user_id: int) -> bool:
    seven_days = datetime.utcnow() - timedelta(days=7)
    stmt = (
        select(func.count())
        .select_from(Session)
        .where(
            Session.user_id == user_id,
            Session.session_type == "lesson",
            Session.started_at >= seven_days,
            Session.accuracy_percent == 100,
        )
    )
    return ((await session.execute(stmt)).scalar() or 0) >= 7


async def _is_achievement_met(session: AsyncSession, user: User, ach: Achievement) -> bool:
    if ach.condition_type == "streak":
        return user.streak >= ach.condition_value
    if ach.condition_type == "xp":
        return user.total_xp >= ach.condition_value
    if ach.condition_type == "lessons":
        return user.total_lessons_complete >= ach.condition_value
    if ach.condition_type == "words":
        stmt = select(func.count()).select_from(VocabularyItem).where(VocabularyItem.user_id == user.id)
        return ((await session.execute(stmt)).scalar() or 0) >= ach.condition_value
    if ach.condition_type == "words_mastered":
        stmt = (
            select(func.count())
            .select_from(VocabularyItem)
            .where(VocabularyItem.user_id == user.id, VocabularyItem.status == "mastered")
        )
        return ((await session.execute(stmt)).scalar() or 0) >= ach.condition_value
    if ach.condition_type == "perfect":
        return await _has_perfect_week(session, user.id)
    if ach.condition_type == "custom":
        if ach.achievement_id == "quick-learner":
            today = datetime.utcnow().date()
            start = datetime(today.year, today.month, today.day)
            end = start + timedelta(days=1)
            stmt = (
                select(func.count())
                .select_from(Session)
                .where(
                    Session.user_id == user.id,
                    Session.session_type == "lesson",
                    Session.started_at >= start,
                    Session.started_at < end,
                )
            )
            return ((await session.execute(stmt)).scalar() or 0) >= ach.condition_value
        return False
    return False


async def check_and_award_achievements(session: AsyncSession, user_id: int) -> list[Achievement]:
    user_stmt = select(User).where(User.id == user_id)
    user = (await session.execute(user_stmt)).scalar_one_or_none()
    if not user:
        return []

    earned_stmt = select(UserAchievement.achievement_id).where(UserAchievement.user_id == user_id)
    earned_ids = set((await session.execute(earned_stmt)).scalars().all())

    all_stmt = select(Achievement).order_by(desc(Achievement.xp_reward))
    all_achievements = (await session.execute(all_stmt)).scalars().all()

    now = datetime.utcnow()
    newly_earned: list[Achievement] = []
    earned_list = list(user.achievements_earned or [])

    for ach in all_achievements:
        if ach.achievement_id in earned_ids:
            continue
        if not await _is_achievement_met(session, user, ach):
            continue

        newly_earned.append(ach)
        session.add(UserAchievement(user_id=user_id, achievement_id=ach.achievement_id, earned_at=now))

        user.xp += ach.xp_reward
        user.total_xp += ach.xp_reward
        earned_list.append(ach.achievement_id)

    if newly_earned:
        user.achievements_earned = earned_list
        user.updated_at = now
        session.add(user)
        await session.commit()

    return newly_earned

