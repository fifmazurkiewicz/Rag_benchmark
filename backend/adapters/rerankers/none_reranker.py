"""Passthrough — no reranking, baseline for comparison."""
from backend.registry import register
from backend.interfaces.pipeline import Chunk


@register("reranker", "none")
class NoneReranker:
    def __init__(self, config=None): pass

    def rerank(self, query: str, chunks: list[Chunk], top_k: int) -> list[Chunk]:
        return chunks[:top_k]
