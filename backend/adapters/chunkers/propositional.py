from __future__ import annotations
import json
import re
import uuid
from typing import Any
from backend.registry import register
from backend.interfaces import Document, Chunk

_SYSTEM = (
    "You are a text processing assistant. "
    "Break the following text into atomic propositions — each chunk should be a "
    "single, self-contained factual statement. Return a JSON array of strings. "
    "Do not add explanations, only return the JSON array."
)


@register("chunker", "propositional")
class PropositionalChunker:
    """Uses an LLM to decompose text into atomic propositions."""

    def __init__(self, config: dict[str, Any]):
        self._llm_model = config.get("llm_model", "claude-haiku-4-5-20251001")
        self._client = None

    def _get_client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic()
        return self._client

    def chunk(self, doc: Document) -> list[Chunk]:
        client = self._get_client()
        response = client.messages.create(
            model=self._llm_model,
            max_tokens=4096,
            system=_SYSTEM,
            messages=[{"role": "user", "content": doc.text}],
        )
        raw = response.content[0].text.strip()
        json_str = re.search(r"\[.*\]", raw, re.DOTALL)
        propositions: list[str] = json.loads(json_str.group()) if json_str else [doc.text]

        return [
            Chunk(
                id=str(uuid.uuid4()),
                doc_id=doc.id,
                text=prop,
                index=i,
                metadata={"chunker": "propositional"},
            )
            for i, prop in enumerate(propositions)
            if prop.strip()
        ]
