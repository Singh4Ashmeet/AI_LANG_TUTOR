from __future__ import annotations

from datetime import datetime, timezone
from bson import ObjectId

from ..database import achievements_collection, users_collection, notifications_collection

ACHIEVEMENTS = [
    {"achievement_id": "first_lesson", "title": "First Lesson", "description": "Complete any lesson", "icon": "✅", "xp_reward": 10, "condition_type": "lessons", "condition_value": 1, "rarity": "common"},
    {"achievement_id": "first_streak", "title": "First Streak", "description": "Reach a 3-day streak", "icon": "🔥", "xp_reward": 15, "condition_type": "streak", "condition_value": 3, "rarity": "common"},
    {"achievement_id": "word_collector", "title": "Word Collector", "description": "Add 10 vocabulary words", "icon": "📚", "xp_reward": 10, "condition_type": "words", "condition_value": 10, "rarity": "common"},
    {"achievement_id": "quick_learner", "title": "Quick Learner", "description": "Complete 5 lessons in one day", "icon": "⚡", "xp_reward": 20, "condition_type": "custom", "condition_value": 5, "rarity": "common"},
    {"achievement_id": "week_warrior", "title": "Week Warrior", "description": "Reach a 7-day streak", "icon": "🏆", "xp_reward": 25, "condition_type": "streak", "condition_value": 7, "rarity": "rare"},
    {"achievement_id": "half_century", "title": "Half Century", "description": "Complete 50 lessons", "icon": "🎯", "xp_reward": 50, "condition_type": "lessons", "condition_value": 50, "rarity": "rare"},
    {"achievement_id": "vocab_champion", "title": "Vocabulary Champion", "description": "Master 100 words", "icon": "📘", "xp_reward": 50, "condition_type": "words", "condition_value": 100, "rarity": "rare"},
    {"achievement_id": "perfect_week", "title": "Perfect Week", "description": "7 perfect lessons in a row", "icon": "⭐", "xp_reward": 60, "condition_type": "perfect", "condition_value": 7, "rarity": "rare"},
    {"achievement_id": "roleplay_rookie", "title": "Roleplay Rookie", "description": "Complete all 8 base scenarios", "icon": "🎭", "xp_reward": 40, "condition_type": "custom", "condition_value": 8, "rarity": "rare"},
    {"achievement_id": "month_master", "title": "Month Master", "description": "Reach a 30-day streak", "icon": "📅", "xp_reward": 80, "condition_type": "streak", "condition_value": 30, "rarity": "epic"},
    {"achievement_id": "section_conqueror", "title": "Section Conqueror", "description": "Complete any full section", "icon": "🧭", "xp_reward": 80, "condition_type": "custom", "condition_value": 1, "rarity": "epic"},
    {"achievement_id": "grammarian", "title": "Grammarian", "description": "Reduce all grammar error rates below 20%", "icon": "🧠", "xp_reward": 80, "condition_type": "custom", "condition_value": 20, "rarity": "epic"},
    {"achievement_id": "dual_linguist", "title": "Dual Linguist", "description": "Enroll in a second language", "icon": "🌐", "xp_reward": 80, "condition_type": "custom", "condition_value": 2, "rarity": "epic"},
    {"achievement_id": "journal_keeper", "title": "Journal Keeper", "description": "Write 10 journal entries", "icon": "📓", "xp_reward": 80, "condition_type": "custom", "condition_value": 10, "rarity": "epic"},
    {"achievement_id": "century_streak", "title": "Century Streak", "description": "Reach a 100-day streak", "icon": "💯", "xp_reward": 150, "condition_type": "streak", "condition_value": 100, "rarity": "legendary"},
    {"achievement_id": "polyglot", "title": "Polyglot", "description": "Reach B2 in any language", "icon": "🌟", "xp_reward": 150, "condition_type": "custom", "condition_value": 1, "rarity": "legendary"},
    {"achievement_id": "crown_royale", "title": "Crown Royale", "description": "Get all crowns to Level 3+", "icon": "👑", "xp_reward": 150, "condition_type": "crowns", "condition_value": 3, "rarity": "legendary"},
    {"achievement_id": "immersionist", "title": "The Immersionist", "description": "Use Immersion Mode for 7 days straight", "icon": "🛰️", "xp_reward": 150, "condition_type": "custom", "condition_value": 7, "rarity": "legendary"},
    {"achievement_id": "fluency_master", "title": "Fluency Master", "description": "Reach C1 level", "icon": "🏅", "xp_reward": 150, "condition_type": "custom", "condition_value": 1, "rarity": "legendary"},
]


async def seed_achievements() -> None:
    now = datetime.now(timezone.utc)
    for achievement in ACHIEVEMENTS:
        doc = {**achievement, "created_at": now}
        await achievements_collection().update_one(
            {"achievement_id": achievement["achievement_id"]},
            {"$setOnInsert": doc},
            upsert=True,
        )


async def check_and_award_achievements(user_id: str) -> list[dict]:
    user = await users_collection().find_one({"_id": ObjectId(user_id)})
    if not user:
        return []

    earned_ids = set(user.get("achievements", []))
    all_achievements = await achievements_collection().find({}).to_list(length=100)
    
    newly_earned = []
    now = datetime.now(timezone.utc)

    for ach in all_achievements:
        ach_id = ach["achievement_id"]
        if ach_id in earned_ids:
            continue
        
        condition_type = ach.get("condition_type")
        condition_value = ach.get("condition_value")
        is_met = False

        if condition_type == "lessons":
            if int(user.get("total_lessons_complete", 0)) >= int(condition_value):
                is_met = True
        elif condition_type == "streak":
            if int(user.get("streak", 0)) >= int(condition_value):
                is_met = True
        elif condition_type == "xp":
            if int(user.get("xp", 0)) >= int(condition_value):
                is_met = True
        # More complex conditions can be added here
        
        if is_met:
            newly_earned.append(ach)
            await users_collection().update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$addToSet": {"achievements": ach_id},
                    "$inc": {"xp": ach.get("xp_reward", 0)}
                }
            )
            # Create notification
            await notifications_collection().insert_one({
                "user_id": ObjectId(user_id),
                "type": "achievement",
                "title": f"Achievement Earned: {ach['title']}",
                "message": ach["description"],
                "icon": ach.get("icon", "🏆"),
                "is_read": False,
                "created_at": now
            })

    return newly_earned
