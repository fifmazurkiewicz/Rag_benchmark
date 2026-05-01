from __future__ import annotations
from typing import Protocol, runtime_checkable
from .pipeline import Chunk


@runtime_checkable
class RerankerAdapter(Protocol):
    def rerank(self, query: str, chunks: list[Chunk], top_k: int) -> list[Chunk]: ...
