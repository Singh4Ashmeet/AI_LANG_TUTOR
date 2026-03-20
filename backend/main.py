from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import structlog
import uuid
import time

from .config import settings
from .database import get_session, init_db
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
from .services.achievements import seed_achievements
from .services.seed import seed_admin
from .services.speech import load_whisper_model

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async for session in get_session():
        await seed_admin(session)
        await seed_achievements(session)
        break
    try:
        load_whisper_model()
    except Exception as exc:
        logger.warning("whisper_load_failed", error=str(exc))
    yield

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info("request", path=request.url.path, method=request.method, status=response.status_code, request_id=request_id, duration=duration)
    response.headers["X-Request-ID"] = request_id
    return response

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", error=str(exc), request_id=getattr(request.state, "request_id", None))
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.VERSION}

# Core Duolingo Clone Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(users.history_router)
app.include_router(users.onboarding_router)
app.include_router(lessons.router)
app.include_router(curriculum.router)
app.include_router(leaderboard.router)
app.include_router(achievements.router)
app.include_router(notifications.router)
app.include_router(chat.router)
app.include_router(roleplay.router)
app.include_router(placement.router)
app.include_router(flashcards.router)
app.include_router(voice.router)
app.include_router(bonus.router)
app.include_router(journal.router)
app.include_router(grammar.router)
app.include_router(word_of_day.router)
app.include_router(admin.router)
