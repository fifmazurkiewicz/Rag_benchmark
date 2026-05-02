"""
OpenRouter LLM reranker — listwise ranking, single API call.

Sends all candidate passages to the LLM in one request and asks it to
return a ranked ordering. Works with any chat model on OpenRouter.

Usage in experiment config:
  reranker: openrouter
  reranker_model: anthropic/claude-haiku-4-5-20251001   (default)
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from backend.config import DEFAULT_RERANKER_MODEL, DEFAULT_RERANKER_MAX_TOKENS
from backend.registry import register
from backend.interfaces.pipeline import Chunk

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a relevance ranking assistant. "
    "Given a question and a list of passages, rank the passages from most to least relevant. "
    "Output ONLY a valid JSON array of the passage indices (0-based), most relevant first. "
    "Example: [2, 0, 3, 1]"
)
_CHUNK_PREVIEW_CHARS = 600


@register("reranker", "openrouter")
class OpenRouterReranker:
    def __init__(self, config: dict[str, Any] | None = None):
        from backend.services.openrouter_client import create_openrouter_client

        cfg = config or {}
        self._model  = cfg.get("reranker_model", DEFAULT_RERANKER_MODEL)
        self._client = create_openrouter_client(cfg.get("openrouter_api_key"))

    def rerank(self, query: str, chunks: list[Chunk], top_k: int) -> list[Chunk]:
        if not chunks:
            return []

        passages = "\n\n".join(
            f"[{i}] {c.text[:_CHUNK_PREVIEW_CHARS]}" for i, c in enumerate(chunks)
        )
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=DEFAULT_RERANKER_MAX_TOKENS,
            temperature=0,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": f"Question: {query}\n\nPassages:\n{passages}"},
            ],
        )
        raw   = response.choices[0].message.content or "[]"
        order = _parse_ranking(raw, len(chunks))

        result = []
        for rank, idx in enumerate(order[:top_k]):
            chunk = chunks[idx]
            chunk.metadata["rerank_score"] = 1.0 - rank / max(len(order), 1)
            result.append(chunk)
        return result


def _parse_ranking(text: str, n: int) -> list[int]:
    """Extract integer array from LLM output; fall back to identity order on failure."""
    try:
        match = re.search(r"\[[\d,\s]+\]", text)
        if match:
            order  = json.loads(match.group())
            valid  = [i for i in order if isinstance(i, int) and 0 <= i < n]
            seen: set[int] = set()
            deduped = [i for i in valid if not (i in seen or seen.add(i))]  # type: ignore[func-returns-value]
            missing = [i for i in range(n) if i not in seen]
            return deduped + missing
    except Exception:
        logger.warning("Could not parse reranker ranking from: %r", text[:200])
    return list(range(n))
