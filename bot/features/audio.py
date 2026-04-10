"""Voice transcription via Whisper-compatible API."""
from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

STT_BASE_URL = os.environ.get("STT_BASE_URL", "https://api.groq.com/openai/v1")
STT_API_KEY = os.environ.get("STT_API_KEY", "")
STT_MODEL = os.environ.get("STT_MODEL", "whisper-large-v3-turbo")


async def transcribe(audio_bytes: bytes, filename: str = "audio.ogg") -> str | None:
    """Transcribe audio bytes. Returns text or None on failure."""
    if not STT_API_KEY:
        logger.warning("STT_API_KEY not set, skipping voice transcription")
        return None

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{STT_BASE_URL}/audio/transcriptions",
                headers={"Authorization": f"Bearer {STT_API_KEY}"},
                files={"file": (filename, audio_bytes, "audio/ogg")},
                data={"model": STT_MODEL},
            )
            resp.raise_for_status()
            text = resp.json().get("text", "").strip()
            if text:
                logger.info("Transcribed %d bytes -> %d chars", len(audio_bytes), len(text))
                return text
            return None
    except Exception:
        logger.exception("Voice transcription failed")
        return None
