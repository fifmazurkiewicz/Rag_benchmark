from __future__ import annotations
from typing import Any
import uuid
from backend.registry import register
from backend.interfaces import Chunk


@register("vector_store", "qdrant")
class QdrantVectorStore:
    def __init__(self, config: dict[str, Any]):
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams
        self._collection = config.get("collection_name", "rag_bench")
        self._dim = int(config.get("embedding_dim", 1536))
        self._client = QdrantClient(
            host=config.get("qdrant_host", "localhost"),
            port=int(config.get("qdrant_port", 6333)),
        )
        self._ensure_collection()

    def _ensure_collection(self):
        from qdrant_client.models import Distance, VectorParams
        existing = [c.name for c in self._client.get_collections().collections]
        if self._collection not in existing:
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(size=self._dim, distance=Distance.COSINE),
            )

    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        from qdrant_client.models import PointStruct
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vec,
                payload={"text": chunk.text, "chunk_id": chunk.id, "doc_id": chunk.doc_id, **chunk.metadata},
            )
            for chunk, vec in zip(chunks, vectors)
        ]
        self._client.upsert(collection_name=self._collection, points=points)

    def search(self, query_vec: list[float], top_k: int) -> list[Chunk]:
        results = self._client.search(
            collection_name=self._collection,
            query_vector=query_vec,
            limit=top_k,
        )
        return [
            Chunk(
                id=r.payload.get("chunk_id", str(r.id)),
                doc_id=r.payload.get("doc_id", ""),
                text=r.payload["text"],
                index=0,
                metadata={"score": r.score},
            )
            for r in results
        ]

    def delete(self) -> None:
        self._client.delete_collection(self._collection)
