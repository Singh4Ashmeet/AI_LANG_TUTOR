from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from difflib import SequenceMatcher

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
    
    matcher = SequenceMatcher(None, expected, actual)
    ratio = matcher.ratio()
    score = int(ratio * 100)
    
    feedback = []
    if score >= 90:
        feedback.append("Excellent pronunciation!")
    elif score >= 70:
        feedback.append("Good job, but watch your clarity.")
    else:
        feedback.append("Try again, focusing on the highlighted words.")

    # Simple diff feedback
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'replace':
            feedback.append(f"Check '{expected[i1:i2]}'.")
        elif tag == 'delete':
            feedback.append(f"You missed '{expected[i1:i2]}'.")
        elif tag == 'insert':
            feedback.append(f"You added extra sounds near '{expected[max(0, i1-1):i1]}'.")

    return {
        "score": score,
        "feedback": " ".join(feedback[:3]),  # Limit feedback length
        "expected": payload.expected_text,
        "actual": payload.recognized_text,
    }
