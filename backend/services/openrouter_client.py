"""Factory for the shared OpenRouter HTTP client (openai-compatible)."""
from __future__ import annotations

import os

from backend.config import OPENROUTER_BASE_URL, OPENROUTER_REFERER, OPENROUTER_TITLE


def create_openrouter_client(api_key: str | None = None):
    """Return a configured openai.OpenAI client pointed at OpenRouter."""
    import openai

    resolved_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
    return openai.OpenAI(
        api_key=resolved_key,
        base_url=OPENROUTER_BASE_URL,
        default_headers={
            "HTTP-Referer": OPENROUTER_REFERER,
            "X-Title": OPENROUTER_TITLE,
        },
    )
