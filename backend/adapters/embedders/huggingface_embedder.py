from __future__ import annotations
from typing import Any
from backend.registry import register


@register("embedder", "hf/bge-large-en")
@register("embedder", "hf/all-MiniLM-L6-v2")
@register("embedder", "hf/multilingual-e5-large")
class HuggingFaceEmbedder:
    def __init__(self, config: dict[str, Any]):
        from sentence_transformers import SentenceTransformer
        model_key = config.get("model", "hf/all-MiniLM-L6-v2")
        model_name = {
            "hf/bge-large-en": "BAAI/bge-large-en-v1.5",
            "hf/all-MiniLM-L6-v2": "sentence-transformers/all-MiniLM-L6-v2",
            "hf/multilingual-e5-large": "intfloat/multilingual-e5-large",
        }.get(model_key, model_key.split("/")[-1])
        self._model = SentenceTransformer(model_name)
        self._dim = self._model.get_sentence_embedding_dimension()

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts, convert_to_numpy=False).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self._model.encode([text], convert_to_numpy=False)[0].tolist()

    def dimension(self) -> int:
        return self._dim
