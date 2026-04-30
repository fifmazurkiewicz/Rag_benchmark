from __future__ import annotations
from typing import Protocol, runtime_checkable
from .pipeline import Document, Chunk


@runtime_checkable
class ChunkerAdapter(Protocol):
    def chunk(self, doc: Document) -> list[Chunk]: ...
