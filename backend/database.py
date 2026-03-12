from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from .config import settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongodb_url)
    return _client


def get_db() -> AsyncIOMotorDatabase:
    return get_client().get_default_database()


def users_collection():
    return get_db()["users"]


def sessions_collection():
    return get_db()["sessions"]


def vocabulary_collection():
    return get_db()["vocabulary"]


def grammar_stats_collection():
    return get_db()["grammar_stats"]


def admin_logs_collection():
    return get_db()["admin_logs"]

def active_sessions_collection():
    return get_db()["active_sessions"]


def otp_codes_collection():
    return get_db()["otp_codes"]


def curriculum_collection():
    return get_db()["curriculum"]


def achievements_collection():
    return get_db()["achievements"]


def leaderboard_entries_collection():
    return get_db()["leaderboard_entries"]


def word_of_day_collection():
    return get_db()["word_of_day"]


def friend_connections_collection():
    return get_db()["friend_connections"]


def challenges_collection():
    return get_db()["challenges"]


def notifications_collection():
    return get_db()["notifications"]


def stories_collection():
    return get_db()["stories"]


async def init_indexes() -> None:
    users = users_collection()
    await users.create_index("email", unique=True)
    await users.create_index("username", unique=True)
    await users.create_index("role")
    await users.create_index("cefr_level")
    await users.create_index("is_active")

    vocab = vocabulary_collection()
    await vocab.create_index([("user_id", 1), ("next_review", 1)])
    await vocab.create_index([("user_id", 1), ("status", 1)])

    sessions = sessions_collection()
    await sessions.create_index("user_id")
    await sessions.create_index([("started_at", -1)])

    grammar = grammar_stats_collection()
    await grammar.create_index([("user_id", 1), ("rule", 1)], unique=True)

    logs = admin_logs_collection()
    await logs.create_index([("created_at", -1)])
    await logs.create_index("event_type")

    active_sessions = active_sessions_collection()
    await active_sessions.create_index("user_id", unique=True)
    await active_sessions.create_index([("last_active", -1)])

    otp_codes = otp_codes_collection()
    await otp_codes.create_index([("email", 1), ("purpose", 1)])
    await otp_codes.create_index("created_at", expireAfterSeconds=900)

    leaderboard = leaderboard_entries_collection()
    await leaderboard.create_index([("week_start", -1), ("rank", 1)])
    await leaderboard.create_index("user_id")

    curriculum = curriculum_collection()
    await curriculum.create_index("language_pair", unique=True)

    word_of_day = word_of_day_collection()
    await word_of_day.create_index([("date", -1), ("language_pair", 1)], unique=True)

    achievements = achievements_collection()
    await achievements.create_index("achievement_id", unique=True)

    friends = friend_connections_collection()
    await friends.create_index([("requester_id", 1), ("receiver_id", 1)], unique=True)

    challenges = challenges_collection()
    await challenges.create_index([("challenger_id", 1), ("challenged_id", 1)])

    notifications = notifications_collection()
    await notifications.create_index([("user_id", 1), ("created_at", -1)])
    await notifications.create_index("is_read")

    stories = stories_collection()
    await stories.create_index([("user_id", 1), ("created_at", -1)])
