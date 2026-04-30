from __future__ import annotations
import re
import uuid
from typing import Any
from backend.registry import register
from backend.interfaces import Document, Chunk


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


@register("chunker", "sentence")
class SentenceChunker:
    def __init__(self, config: dict[str, Any]):
        self.sentences_per_chunk = int(config.get("sentences_per_chunk", 5))
        self.overlap_sentences = int(config.get("overlap_sentences", 1))

    def chunk(self, doc: Document) -> list[Chunk]:
        sentences = _split_sentences(doc.text)
        chunks: list[Chunk] = []
        step = max(1, self.sentences_per_chunk - self.overlap_sentences)
        for i, start in enumerate(range(0, len(sentences), step)):
            group = sentences[start : start + self.sentences_per_chunk]
            text = " ".join(group)
            if not text.strip():
                continue
            chunks.append(Chunk(
                id=str(uuid.uuid4()),
                doc_id=doc.id,
                text=text,
                index=i,
                metadata={"chunker": "sentence", "sentence_start": start},
            ))
        return chunks
