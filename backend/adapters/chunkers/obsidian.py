"""
Obsidian-aware chunker.

Respects Obsidian's structure:
  - Splits on H1/H2/H3 headings (each section = chunk)
  - Preserves section heading as chunk title metadata
  - Attaches backlink_titles as extra context (Karpathy's key insight:
    notes that LINK TO this note add implicit context)
  - Falls back to fixed chunking if a section is too long
"""
from __future__ import annotations
import re
import uuid
from typing import Any
from backend.registry import register
from backend.interfaces import Document, Chunk

_HEADING = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)


@register("chunker", "obsidian")
class ObsidianChunker:

    def __init__(self, config: dict[str, Any]):
        self.max_words   = int(config.get("chunk_size", 400))
        self.split_depth = int(config.get("split_depth", 2))   # 1=H1 only, 2=H1+H2, 3=all

    def chunk(self, doc: Document) -> list[Chunk]:
        text     = doc.text
        title    = doc.metadata.get("title", "")
        backlinks = doc.metadata.get("backlink_titles", [])

        # Prepend backlink context (Karpathy approach: who links here?)
        backlink_ctx = ""
        if backlinks:
            backlink_ctx = f"[Referenced by: {', '.join(backlinks[:5])}]\n\n"

        # Split by headings up to split_depth
        sections: list[tuple[str, str]] = []   # (heading_text, body)
        last_end  = 0
        last_head = title or "Introduction"

        for m in _HEADING.finditer(text):
            depth = len(m.group(1))
            if depth > self.split_depth:
                continue
            body = text[last_end : m.start()].strip()
            if body:
                sections.append((last_head, body))
            last_head = m.group(2).strip()
            last_end  = m.end()

        tail = text[last_end:].strip()
        if tail:
            sections.append((last_head, tail))

        if not sections:
            sections = [(title, text)]

        chunks: list[Chunk] = []
        for heading, body in sections:
            # Prepend backlink context only to first chunk of the note
            prefix    = backlink_ctx if not chunks else ""
            full_text = f"{prefix}## {heading}\n{body}" if heading else f"{prefix}{body}"
            words     = full_text.split()

            if len(words) <= self.max_words:
                chunks.append(Chunk(
                    id=str(uuid.uuid4()),
                    doc_id=doc.id,
                    text=full_text,
                    index=len(chunks),
                    metadata={
                        "chunker":  "obsidian",
                        "heading":  heading,
                        "title":    title,
                        "backlinks": backlinks,
                        "tags":     doc.metadata.get("tags", []),
                    },
                ))
            else:
                # Section too long — sub-chunk by paragraphs
                paras = [p.strip() for p in re.split(r"\n{2,}", body) if p.strip()]
                current: list[str] = [f"## {heading}"] if heading else []
                for para in paras:
                    candidate = current + [para]
                    if len(" ".join(candidate).split()) <= self.max_words:
                        current = candidate
                    else:
                        if current:
                            chunks.append(Chunk(
                                id=str(uuid.uuid4()),
                                doc_id=doc.id,
                                text="\n\n".join(current),
                                index=len(chunks),
                                metadata={"chunker": "obsidian", "heading": heading, "title": title},
                            ))
                        current = [para]
                if current:
                    chunks.append(Chunk(
                        id=str(uuid.uuid4()),
                        doc_id=doc.id,
                        text="\n\n".join(current),
                        index=len(chunks),
                        metadata={"chunker": "obsidian", "heading": heading, "title": title},
                    ))

        return chunks
