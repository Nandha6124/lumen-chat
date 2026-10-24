import time
from typing import Dict, List

import httpx

from .config import settings

SYSTEM_PROMPT = (
    "You are Lumen, a friendly and concise AI assistant. Use earlier messages for context. "
    "If you are unsure, say so instead of guessing."
)
URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
RETRY_STATUS = {429, 500, 502, 503, 504}
RETRIES_PER_MODEL = 2


class LLMError(Exception):
    pass


def _call_model(model: str, payload: dict) -> str:
    last = "unknown error"
    for attempt in range(RETRIES_PER_MODEL + 1):
        try:
            r = httpx.post(
                URL.format(model=model),
                headers={"x-goog-api-key": settings.gemini_api_key},
                json=payload,
                timeout=40,
            )
            if r.status_code in RETRY_STATUS:
                last = f"HTTP {r.status_code}"
            else:
                r.raise_for_status()
                return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        except httpx.TransportError as exc:
            last = str(exc)
        except httpx.HTTPStatusError as exc:
            raise LLMError(f"The AI service failed: {exc}") from exc
        except (KeyError, IndexError) as exc:
            raise LLMError("The AI service returned an unexpected response") from exc
        if attempt < RETRIES_PER_MODEL:
            time.sleep(2 ** attempt)
    raise LLMError(f"{model} is busy ({last})")


def generate_reply(history: List[Dict[str, str]]) -> str:
    """Tries the main model, then the fallback model if the main one stays busy."""
    if not settings.gemini_api_key:
        raise LLMError("The AI service is not configured (missing GEMINI_API_KEY)")
    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [
            {"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]}
            for m in history
        ],
        "generationConfig": {"temperature": 0.4},
    }
    errors = []
    for model in dict.fromkeys([settings.gemini_model, settings.gemini_fallback_model]):
        try:
            return _call_model(model, payload)
        except LLMError as exc:
            if "busy" not in str(exc):
                raise
            errors.append(str(exc))
    raise LLMError("The AI service is busy right now. Please try again in a moment.")
