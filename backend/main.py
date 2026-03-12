from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from .config import AppInfo, settings
from .database import init_indexes
from .limiters import limiter
from .routers import (
    achievements,
    admin,
    auth,
    bonus,
    chat,
    curriculum,
    flashcards,
    grammar,
    journal,
    leaderboard,
    lessons,
    notifications,
    placement,
    roleplay,
    users,
    voice,
    word_of_day,
)
from .services.seed import seed_admin
from .services.achievements import seed_achievements
from .services.speech import load_whisper_model

app_info = AppInfo()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_indexes()
    await seed_admin()
    await seed_achievements()
    load_whisper_model()
    yield


app = FastAPI(title=app_info.name, version=app_info.version, lifespan=lifespan)
app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Too many requests. Please try again later."})


@app.get("/")
async def root():
    return {"name": app_info.name, "version": app_info.version}


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(users.history_router)
app.include_router(users.onboarding_router)
app.include_router(curriculum.router)
app.include_router(lessons.router)
app.include_router(chat.router)
app.include_router(roleplay.router)
app.include_router(flashcards.router)
app.include_router(voice.router)
app.include_router(placement.router)
app.include_router(bonus.router)
app.include_router(grammar.router)
app.include_router(journal.router)
app.include_router(leaderboard.router)
app.include_router(achievements.router)
app.include_router(word_of_day.router)
app.include_router(notifications.router)
app.include_router(admin.router)
