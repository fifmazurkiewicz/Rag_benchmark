"""
Cohere Rerank API — cloud-based reranker, best quality for Polish + English.

Cohere's rerank-v3.5 model scores (query, passage) relevance directly,
similar to cross-encoders but hosted. Supports multilingual text.

Available via direct Cohere API or OpenRouter:
  rerank-v3.5           — best quality (multilingual)
  rerank-english-v3.0   — English-only, slightly faster
  rerank-multilingual-v3.0 — older multilingual

Usage in experiment config:
  reranker: cohere
  cohere_model: rerank-v3.5          (default)
  cohere_api_key: <key>              (or COHERE_API_KEY env var)
"""
from __future__ import annotations

import os
from typing import Any

from backend.registry import register
from backend.interfaces.pipeline import Chunk


@register("reranker", "cohere")
class CohereReranker:
    def __init__(self, config: dict[str, Any] | None = None):
        import cohere
        cfg = config or {}
        model = cfg.get("cohere_model", "rerank-v3.5")
        api_key = cfg.get("cohere_api_key") or os.environ["COHERE_API_KEY"]
        self._client = cohere.Client(api_key=api_key)
        self._model = model

    def rerank(self, query: str, chunks: list[Chunk], top_k: int) -> list[Chunk]:
        if not chunks:
            return []
        docs = [c.text for c in chunks]
        response = self._client.rerank(
            model=self._model,
            query=query,
            documents=docs,
            top_n=top_k,
        )
        result = []
        for hit in response.results:
            chunk = chunks[hit.index]
            chunk.metadata["rerank_score"] = float(hit.relevance_score)
            result.append(chunk)
        return result
