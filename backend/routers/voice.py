from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from ..dependencies import get_current_user
from ..services.speech import synthesize_speech, transcribe_audio

router = APIRouter(prefix="/voice", tags=["voice"])


class TTSRequest(BaseModel):
    text: str
    language: str
    persona: str


class PronunciationRequest(BaseModel):
    expected_text: str
    recognized_text: str


@router.post("/stt")
async def speech_to_text(file: UploadFile = File(...), user=Depends(get_current_user)):
    data = await file.read()
    result = await transcribe_audio(data)
    return result


@router.post("/tts")
async def text_to_speech(payload: TTSRequest, user=Depends(get_current_user)):
    audio = await synthesize_speech(payload.text, payload.language, payload.persona)
    return Response(content=audio, media_type="audio/mpeg")


@router.post("/pronunciation-score")
async def pronunciation_score(payload: PronunciationRequest, user=Depends(get_current_user)):
    expected = payload.expected_text.strip().lower()
    actual = payload.recognized_text.strip().lower()
    score = 100 if expected == actual else max(0, 70 - abs(len(expected) - len(actual)))
    return {
        "score": score,
        "feedback": "Keep practicing individual syllables for clearer pronunciation.",
        "expected": payload.expected_text,
        "actual": payload.recognized_text,
    }
