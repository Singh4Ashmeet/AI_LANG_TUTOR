from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, WebSocket, status
from pydantic import BaseModel

from ..database import sessions_collection, vocabulary_collection
from ..dependencies import get_current_user
from ..services.learner import apply_sm2

router = APIRouter(prefix="/flashcards", tags=["flashcards"])

_active_battles: dict[str, dict] = {}


class AddCardRequest(BaseModel):
    word: str
    translation: str
    language: str
    context_sentence: str | None = None
    source_session_id: str | None = None


class ReviewRequest(BaseModel):
    card_id: str
    quality: int


class BattleInviteResponse(BaseModel):
    battle_id: str


@router.get("")
async def get_due_cards(user=Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    cursor = vocabulary_collection().find(
        {"user_id": user["_id"], "next_review": {"$lte": now}}
    ).sort("next_review", 1)
    cards = []
    async for item in cursor:
        item["_id"] = str(item["_id"])
        item["user_id"] = str(item["user_id"])
        cards.append(item)
    return {"cards": cards}


@router.post("/add")
async def add_card(payload: AddCardRequest, user=Depends(get_current_user)):
    vocab = vocabulary_collection()
    existing = await vocab.find_one({"user_id": user["_id"], "word": payload.word.lower()})
    if existing:
        return {"card_id": str(existing["_id"])}

    now = datetime.now(timezone.utc)
    result = await vocab.insert_one(
        {
            "user_id": user["_id"],
            "word": payload.word.lower(),
            "translation": payload.translation,
            "language": payload.language,
            "status": "new",
            "ease_factor": 2.5,
            "interval_days": 1,
            "repetitions": 0,
            "next_review": now,
            "last_seen": None,
            "times_seen": 0,
            "times_correct": 0,
            "context_sentence": payload.context_sentence,
            "source_session_id": ObjectId(payload.source_session_id)
            if payload.source_session_id
            else None,
            "created_at": now,
        }
    )
    return {"card_id": str(result.inserted_id)}


@router.post("/review")
async def review_card(payload: ReviewRequest, user=Depends(get_current_user)):
    vocab = vocabulary_collection()
    card = await vocab.find_one({"_id": ObjectId(payload.card_id), "user_id": user["_id"]})
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")

    card["times_seen"] = int(card.get("times_seen", 0)) + 1
    if payload.quality >= 4:
        card["times_correct"] = int(card.get("times_correct", 0)) + 1

    card = apply_sm2(card, payload.quality)
    card["last_seen"] = datetime.now(timezone.utc)
    await vocab.update_one({"_id": card["_id"]}, {"$set": card})

    return {"next_review": card["next_review"], "interval_days": card["interval_days"]}


@router.get("/stats")
async def flashcard_stats(user=Depends(get_current_user)):
    total = await vocabulary_collection().count_documents({"user_id": user["_id"]})
    mastered = await vocabulary_collection().count_documents({"user_id": user["_id"], "status": "mastered"})
    return {"total": total, "mastered": mastered}


@router.post("/battle/invite/{friend_id}", response_model=BattleInviteResponse)
async def invite_battle(friend_id: str, user=Depends(get_current_user)):
    battle_id = str(ObjectId())
    _active_battles[battle_id] = {"players": [str(user["_id"]), friend_id], "started_at": datetime.now(timezone.utc)}
    return {"battle_id": battle_id}


@router.websocket("/battle/{battle_id}")
async def battle_socket(websocket: WebSocket, battle_id: str):
    await websocket.accept()
    if battle_id not in _active_battles:
        await websocket.send_text("Battle not found")
        await websocket.close()
        return
    while True:
        message = await websocket.receive_text()
        await websocket.send_text(message)
