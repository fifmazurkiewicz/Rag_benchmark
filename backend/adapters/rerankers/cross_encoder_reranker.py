"""
Cross-encoder reranker — local, no API cost.

Uses a sentence-transformers cross-encoder model that scores
(query, passage) pairs directly. Significantly better than cosine
similarity for relevance ranking.

Good default: cross-encoder/ms-marco-MiniLM-L-6-v2
  - 80 MB model, runs on CPU
  - Trained on MS MARCO passage retrieval
  - ~100 ms for 20 candidates on modern CPU
"""
from __future__ import annotations
from typing import Any
from backend.registry import register
from backend.interfaces.pipeline import Chunk


@register("reranker", "cross_encoder")
class CrossEncoderReranker:
    def __init__(self, config: dict[str, Any] | None = None):
        from sentence_transformers import CrossEncoder
        model_name = (config or {}).get(
            "cross_encoder_model",
            "cross-encoder/ms-marco-MiniLM-L-6-v2",
        )
        self._model = CrossEncoder(model_name)

    def rerank(self, query: str, chunks: list[Chunk], top_k: int) -> list[Chunk]:
        if not chunks:
            return []
        pairs = [(query, c.text) for c in chunks]
        scores = self._model.predict(pairs)
        ranked = sorted(zip(scores, chunks), key=lambda x: x[0], reverse=True)
        result = []
        for score, chunk in ranked[:top_k]:
            chunk.metadata["rerank_score"] = float(score)
            result.append(chunk)
        return result
