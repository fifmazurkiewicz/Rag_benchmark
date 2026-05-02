from __future__ import annotations
from typing import Protocol, runtime_checkable
from .pipeline import Chunk


@runtime_checkable
class VectorStoreAdapter(Protocol):
    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None: ...
    def search(self, query_vector: list[float], k: int) -> list[Chunk]: ...
