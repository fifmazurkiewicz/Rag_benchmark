from __future__ import annotations
import re
import uuid
from typing import Any
from backend.registry import register
from backend.interfaces import Document, Chunk

_HEADING = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


@register("chunker", "markdown")
class MarkdownChunker:
    def __init__(self, config: dict[str, Any]):
        self.max_size = int(config.get("chunk_size", 1024))

    def chunk(self, doc: Document) -> list[Chunk]:
        sections: list[tuple[str, str]] = []
        last_end = 0
        last_heading = "root"
        for m in _HEADING.finditer(doc.text):
            body = doc.text[last_end : m.start()].strip()
            if body:
                sections.append((last_heading, body))
            last_heading = m.group(2).strip()
            last_end = m.end()
        tail = doc.text[last_end:].strip()
        if tail:
            sections.append((last_heading, tail))

        chunks: list[Chunk] = []
        for i, (heading, body) in enumerate(sections):
            words = body.split()
            if len(words) <= self.max_size:
                chunks.append(Chunk(
                    id=str(uuid.uuid4()),
                    doc_id=doc.id,
                    text=body,
                    index=i,
                    metadata={"chunker": "markdown", "heading": heading},
                ))
            else:
                for j, start in enumerate(range(0, len(words), self.max_size)):
                    text = " ".join(words[start : start + self.max_size])
                    chunks.append(Chunk(
                        id=str(uuid.uuid4()),
                        doc_id=doc.id,
                        text=text,
                        index=len(chunks),
                        metadata={"chunker": "markdown", "heading": heading, "part": j},
                    ))
        return chunks
