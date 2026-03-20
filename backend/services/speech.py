from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from functools import partial

try:
    from faster_whisper import WhisperModel
except Exception:  # pragma: no cover - optional dependency at runtime
    WhisperModel = None  # type: ignore[assignment]
import edge_tts

from ..config import settings

_whisper_model: WhisperModel | None = None

VOICE_MAP = {
    "en": "en-US-JennyNeural",
    "es": "es-ES-ElviraNeural",
    "fr": "fr-FR-DeniseNeural",
    "de": "de-DE-KatjaNeural",
    "it": "it-IT-ElsaNeural",
    "pt": "pt-BR-FranciscaNeural",
    "ja": "ja-JP-NanamiNeural",
    "ko": "ko-KR-SunHiNeural",
    "zh": "zh-CN-XiaoxiaoNeural",
    "ar": "ar-SA-ZariyahNeural",
    "ru": "ru-RU-SvetlanaNeural",
    "hi": "hi-IN-SwaraNeural",
}

PERSONA_VOICE = {
    "friendly": {"rate": "+5%", "pitch": "+5Hz"},
    "strict": {"rate": "+0%", "pitch": "-5Hz"},
    "funny": {"rate": "+10%", "pitch": "+10Hz"},
    "professor": {"rate": "-5%", "pitch": "+0Hz"},
}


def load_whisper_model() -> None:
    global _whisper_model
    if _whisper_model is None:
        if WhisperModel is None:
            raise RuntimeError("faster-whisper is not installed")
        _whisper_model = WhisperModel(settings.WHISPER_MODEL, device="cpu", compute_type="int8")


def get_whisper_model() -> WhisperModel:
    if _whisper_model is None:
        load_whisper_model()
    return _whisper_model


async def transcribe_audio(data: bytes) -> dict:
    model = get_whisper_model()
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
            tmp.write(data)
            tmp_path = Path(tmp.name)
        
        loop = asyncio.get_running_loop()
        # model.transcribe is blocking, run in executor
        segments, info = await loop.run_in_executor(
            None, 
            partial(model.transcribe, str(tmp_path), vad_filter=True)
        )
        
        text = " ".join(segment.text.strip() for segment in segments)
        return {
            "text": text,
            "language_detected": info.language,
            "confidence": float(info.language_probability),
        }
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


async def synthesize_speech(text: str, language: str, persona: str) -> bytes:
    voice = VOICE_MAP.get(language, VOICE_MAP["en"])
    adjustments = PERSONA_VOICE.get(persona, PERSONA_VOICE["friendly"])
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=adjustments["rate"], pitch=adjustments["pitch"])
    audio_chunks = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_chunks.append(chunk["data"])
    return b"".join(audio_chunks)
