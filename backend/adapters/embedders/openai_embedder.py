from __future__ import annotations
from typing import Any
from backend.registry import register

_DIMENSIONS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}


@register("embedder", "openai/text-embedding-3-small")
@register("embedder", "openai/text-embedding-3-large")
@register("embedder", "openai/text-embedding-ada-002")
class OpenAIEmbedder:
    def __init__(self, config: dict[str, Any]):
        import openai
        model = config.get("model", "text-embedding-3-small")
        self._model = model.split("/")[-1]
        self._client = openai.OpenAI()

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(model=self._model, input=texts)
        return [item.embedding for item in response.data]

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]

    def dimension(self) -> int:
        return _DIMENSIONS.get(self._model, 1536)
