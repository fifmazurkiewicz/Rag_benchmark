"""
OpenRouter embedder — OpenAI-compatible /embeddings endpoint.

OpenRouter routes embedding requests to the underlying provider
(OpenAI, Cohere, etc.) using a single API key and unified billing.

Available embedding models on OpenRouter (as of 2025):
  openai/text-embedding-3-small   — 1536 dims, fast, cheap
  openai/text-embedding-3-large   — 3072 dims, best quality
  openai/text-embedding-ada-002   — 1536 dims, legacy

Usage in experiment config:
  embedder_model: openrouter/text-embedding-3-small
"""
from __future__ import annotations

import os
from typing import Any

from backend.registry import register

_OPENROUTER_BASE = "https://openrouter.ai/api/v1"

_DIMENSIONS: dict[str, int] = {
    "openai/text-embedding-3-small": 1536,
    "openai/text-embedding-3-large": 3072,
    "openai/text-embedding-ada-002":  1536,
}


@register("embedder", "openrouter/text-embedding-3-small")
@register("embedder", "openrouter/text-embedding-3-large")
@register("embedder", "openrouter/text-embedding-ada-002")
class OpenRouterEmbedder:
    def __init__(self, config: dict[str, Any]):
        import openai
        model_key = config.get("model", "openrouter/text-embedding-3-small")
        # strip "openrouter/" prefix → actual model name sent to API
        self._model = model_key.removeprefix("openrouter/")
        self._client = openai.OpenAI(
            api_key=config.get("openrouter_api_key") or os.environ["OPENROUTER_API_KEY"],
            base_url=_OPENROUTER_BASE,
            default_headers={
                "HTTP-Referer": "https://github.com/fifmazurkiewicz/Rag_benchmark",
                "X-Title": "RAG Benchmark",
            },
        )
        self._dim = _DIMENSIONS.get(self._model, 1536)

    def embed(self, texts: list[str]) -> list[list[float]]:
        # OpenRouter has a batch limit — chunk into batches of 100
        all_vecs: list[list[float]] = []
        for i in range(0, len(texts), 100):
            batch = texts[i : i + 100]
            resp = self._client.embeddings.create(model=self._model, input=batch)
            all_vecs.extend(item.embedding for item in resp.data)
        return all_vecs

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]

    def dimension(self) -> int:
        return self._dim
