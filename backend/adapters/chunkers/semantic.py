from __future__ import annotations
import re
import uuid
from typing import Any
from backend.registry import register
from backend.interfaces import Document, Chunk


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


@register("chunker", "semantic")
class SemanticChunker:
    """Groups sentences until cosine similarity drops below threshold."""

    def __init__(self, config: dict[str, Any]):
        self.threshold = float(config.get("similarity_threshold", 0.75))
        self._embedder = None
        self._embedder_name = config.get("embedder_model", "openai/text-embedding-3-small")

    def _get_embedder(self):
        if self._embedder is None:
            from backend.factory import build_embedder
            self._embedder = build_embedder(
                self._embedder_name,
                {"model": self._embedder_name}
            )
        return self._embedder

    def chunk(self, doc: Document) -> list[Chunk]:
        sentences = _split_sentences(doc.text)
        if not sentences:
            return []

        embedder = self._get_embedder()
        vecs = embedder.embed(sentences)

        chunks: list[Chunk] = []
        group: list[str] = [sentences[0]]
        group_vec = vecs[0]

        for sent, vec in zip(sentences[1:], vecs[1:]):
            sim = _cosine(group_vec, vec)
            if sim >= self.threshold:
                group.append(sent)
                group_vec = [
                    (a * len(group) + b) / (len(group) + 1)
                    for a, b in zip(group_vec, vec)
                ]
            else:
                chunks.append(Chunk(
                    id=str(uuid.uuid4()),
                    doc_id=doc.id,
                    text=" ".join(group),
                    index=len(chunks),
                    metadata={"chunker": "semantic", "size": len(group)},
                ))
                group = [sent]
                group_vec = vec

        if group:
            chunks.append(Chunk(
                id=str(uuid.uuid4()),
                doc_id=doc.id,
                text=" ".join(group),
                index=len(chunks),
                metadata={"chunker": "semantic", "size": len(group)},
            ))
        return chunks
