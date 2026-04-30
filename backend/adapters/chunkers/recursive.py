from __future__ import annotations
import uuid
from typing import Any
from backend.registry import register
from backend.interfaces import Document, Chunk

_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


def _recursive_split(text: str, size: int, overlap: int, separators: list[str]) -> list[str]:
    if not text:
        return []
    sep = separators[0]
    if len(separators) == 1:
        sep = separators[0]
    parts = text.split(sep) if sep else list(text)
    chunks: list[str] = []
    current = ""
    for part in parts:
        candidate = (current + sep + part).strip() if current else part.strip()
        if len(candidate.split()) <= size:
            current = candidate
        else:
            if current:
                chunks.append(current)
            if len(part.split()) > size and len(separators) > 1:
                chunks.extend(_recursive_split(part, size, overlap, separators[1:]))
                current = ""
            else:
                current = part
    if current:
        chunks.append(current)
    return chunks


@register("chunker", "recursive")
class RecursiveChunker:
    def __init__(self, config: dict[str, Any]):
        self.size = int(config.get("chunk_size", 512))
        self.overlap = int(config.get("overlap", 64))

    def chunk(self, doc: Document) -> list[Chunk]:
        raw = _recursive_split(doc.text, self.size, self.overlap, _SEPARATORS)
        return [
            Chunk(
                id=str(uuid.uuid4()),
                doc_id=doc.id,
                text=t,
                index=i,
                metadata={"chunker": "recursive"},
            )
            for i, t in enumerate(raw)
            if t.strip()
        ]
