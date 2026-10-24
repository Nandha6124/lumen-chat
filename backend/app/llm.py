from typing import Dict, List

import httpx

from .config import settings

SYSTEM_PROMPT = (
    "You are Lumen, a friendly and concise AI assistant. Use earlier messages for context. "
    "If you are unsure, say so instead of guessing."
)
URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class LLMError(Exception):
    pass


def generate_reply(history: List[Dict[str, str]]) -> str:
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
    try:
        r = httpx.post(
            URL.format(model=settings.gemini_model),
            headers={"x-goog-api-key": settings.gemini_api_key},
            json=payload,
            timeout=40,
        )
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (httpx.HTTPError, KeyError, IndexError) as exc:
        raise LLMError(f"The AI service failed: {exc}") from exc
