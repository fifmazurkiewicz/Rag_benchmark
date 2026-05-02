"""
HyDE — Hypothetical Document Embeddings (Gao et al., 2022).

Instead of embedding the raw question, the LLM generates a hypothetical
answer first. That answer is embedded and used for vector search.

All LLM calls go through OpenRouter (OPENROUTER_API_KEY).
See docs/hyde.md for full explanation and benchmark guidance.
"""
from __future__ import annotations

import logging
from typing import Any

from backend.config import DEFAULT_HYDE_MODEL, DEFAULT_HYDE_MAX_TOKENS
from backend.registry import register

logger = logging.getLogger(__name__)

_DEFAULT_INSTRUCTION = (
    "You are a helpful assistant. Generate a single short passage (2-4 sentences) "
    "that would directly answer the following question. "
    "Write as if it were an excerpt from a relevant document. "
    "Output only the passage, no preamble."
)


@register("query_transformer", "hyde")
class HyDETransformer:
    def __init__(self, config: dict[str, Any] | None = None):
        from backend.services.openrouter_client import create_openrouter_client

        cfg = config or {}
        self._model       = cfg.get("hyde_model", DEFAULT_HYDE_MODEL)
        self._max_tokens  = int(cfg.get("hyde_max_tokens", DEFAULT_HYDE_MAX_TOKENS))
        self._instruction = cfg.get("hyde_instruction", _DEFAULT_INSTRUCTION)
        self._client      = create_openrouter_client(cfg.get("openrouter_api_key"))

    def transform(self, query: str) -> str:
        """Return a hypothetical answer passage to use as the retrieval query."""
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=[{"role": "user", "content": f"{self._instruction}\n\nQuestion: {query}"}],
        )
        hypothesis = response.choices[0].message.content.strip()
        logger.debug("HyDE: query=%r → hypothesis_len=%d", query[:60], len(hypothesis))
        return hypothesis
