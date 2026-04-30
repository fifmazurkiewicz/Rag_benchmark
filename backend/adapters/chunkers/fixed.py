from __future__ import annotations
import uuid
from typing import Any
from backend.registry import register
from backend.interfaces import Document, Chunk


@register("chunker", "fixed")
class FixedChunker:
    def __init__(self, config: dict[str, Any]):
        self.size = int(config.get("chunk_size", 512))
        self.overlap = int(config.get("overlap", 64))

    def chunk(self, doc: Document) -> list[Chunk]:
        words = doc.text.split()
        chunks: list[Chunk] = []
        step = max(1, self.size - self.overlap)
        for i, start in enumerate(range(0, len(words), step)):
            text = " ".join(words[start : start + self.size])
            if not text.strip():
                continue
            chunks.append(Chunk(
                id=str(uuid.uuid4()),
                doc_id=doc.id,
                text=text,
                index=i,
                metadata={"chunker": "fixed", "start_word": start},
            ))
        return chunks
