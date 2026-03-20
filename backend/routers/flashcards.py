from __future__ import annotations
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, WebSocket, status
from pydantic import BaseModel
from sqlmodel import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_session
from ..dependencies import get_current_user
from ..models.user import User
from ..models.vocabulary import VocabularyItem
from ..services.learner import apply_sm2

router = APIRouter(prefix="/flashcards", tags=["flashcards"])

_active_battles: dict[str, dict] = {}

class AddCardRequest(BaseModel):
    word: str
    translation: str
    language: str
    context_sentence: str | None = None
    source_session_id: int | None = None

class ReviewRequest(BaseModel):
    card_id: int
    quality: int

class BattleInviteResponse(BaseModel):
    battle_id: str

@router.get("")
async def get_due_cards(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    now = datetime.utcnow()
    stmt = select(VocabularyItem).where(
        VocabularyItem.user_id == user.id, 
        VocabularyItem.next_review <= now
    ).order_by(VocabularyItem.next_review)
    result = await session.execute(stmt)
    cards = result.scalars().all()
    items = []
    for card in cards:
        data = card.model_dump()
        data["_id"] = card.id
        items.append(data)
    return {"cards": items}

@router.post("/add")
async def add_card(
    payload: AddCardRequest, 
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(VocabularyItem).where(
        VocabularyItem.user_id == user.id, 
        VocabularyItem.word == payload.word.lower()
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if existing:
        return {"card_id": existing.id}

    now = datetime.utcnow()
    card = VocabularyItem(
        user_id=user.id,
        word=payload.word.lower(),
        translation=payload.translation,
        language=payload.language,
        status="new",
        next_review=now,
        context_sentence=payload.context_sentence,
        source_session_id=payload.source_session_id,
        created_at=now,
    )
    session.add(card)
    await session.commit()
    await session.refresh(card)
    return {"card_id": card.id}

@router.post("/review")
async def review_card(
    payload: ReviewRequest, 
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(VocabularyItem).where(
        VocabularyItem.id == payload.card_id, 
        VocabularyItem.user_id == user.id
    )
    result = await session.execute(stmt)
    card = result.scalar_one_or_none()
    
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")

    card.times_seen = (card.times_seen or 0) + 1
    if payload.quality >= 4:
        card.times_correct = (card.times_correct or 0) + 1

    # apply_sm2 might need to be updated to handle SQLModel object
    card = apply_sm2(card, payload.quality)
    card.last_seen = datetime.utcnow()
    
    session.add(card)
    await session.commit()
    await session.refresh(card)

    return {"next_review": card.next_review, "interval_days": card.interval_days}

@router.get("/stats")
async def flashcard_stats(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    total_stmt = select(func.count()).select_from(VocabularyItem).where(VocabularyItem.user_id == user.id)
    mastered_stmt = select(func.count()).select_from(VocabularyItem).where(
        VocabularyItem.user_id == user.id, 
        VocabularyItem.status == "mastered"
    )
    
    total = (await session.execute(total_stmt)).scalar() or 0
    mastered = (await session.execute(mastered_stmt)).scalar() or 0
    
    return {"total": total, "mastered": mastered}

@router.post("/battle/invite/{friend_id}", response_model=BattleInviteResponse)
async def invite_battle(friend_id: int, user: User = Depends(get_current_user)):
    import uuid
    battle_id = str(uuid.uuid4())
    _active_battles[battle_id] = {"players": [user.id, friend_id], "started_at": datetime.utcnow()}
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
