from __future__ import annotations
import json
import re
import uuid
from typing import Any
from backend.config import DEFAULT_LLM_MODEL
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
        self._llm_model = config.get("llm_model", DEFAULT_LLM_MODEL)
        self._api_key   = config.get("openrouter_api_key")
        self._client    = None

    def _get_client(self):
        if self._client is None:
            from backend.services.openrouter_client import create_openrouter_client
            self._client = create_openrouter_client(self._api_key)
        return self._client

    def chunk(self, doc: Document) -> list[Chunk]:
        response = self._get_client().chat.completions.create(
            model=self._llm_model,
            max_tokens=4096,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user",   "content": doc.text},
            ],
        )
        raw = response.choices[0].message.content or ""
        json_match = re.search(r"\[.*\]", raw, re.DOTALL)
        propositions: list[str] = json.loads(json_match.group()) if json_match else [doc.text]

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
