from __future__ import annotations
from typing import Any
from backend.registry import register
from backend.interfaces import Chunk


@register("vector_store", "elasticsearch")
class ElasticsearchVectorStore:
    def __init__(self, config: dict[str, Any]):
        from elasticsearch import Elasticsearch
        self._index = config.get("es_index", "rag_bench")
        self._dim = int(config.get("embedding_dim", 1536))
        self._client = Elasticsearch(config.get("es_url", "http://localhost:9200"))
        self._ensure_index()

    def _ensure_index(self):
        if not self._client.indices.exists(index=self._index):
            self._client.indices.create(
                index=self._index,
                body={
                    "mappings": {
                        "properties": {
                            "text": {"type": "text"},
                            "doc_id": {"type": "keyword"},
                            "chunk_id": {"type": "keyword"},
                            "embedding": {
                                "type": "dense_vector",
                                "dims": self._dim,
                                "index": True,
                                "similarity": "cosine",
                            },
                        }
                    }
                },
            )

    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        ops = []
        for chunk, vec in zip(chunks, vectors):
            ops.append({"index": {"_index": self._index, "_id": chunk.id}})
            ops.append({
                "text": chunk.text,
                "doc_id": chunk.doc_id,
                "chunk_id": chunk.id,
                "embedding": vec,
                **chunk.metadata,
            })
        self._client.bulk(operations=ops, refresh=True)

    def search(self, query_vec: list[float], top_k: int) -> list[Chunk]:
        resp = self._client.search(
            index=self._index,
            knn={"field": "embedding", "query_vector": query_vec, "k": top_k, "num_candidates": top_k * 5},
        )
        return [
            Chunk(
                id=hit["_source"].get("chunk_id", hit["_id"]),
                doc_id=hit["_source"].get("doc_id", ""),
                text=hit["_source"]["text"],
                index=0,
                metadata={"score": hit["_score"]},
            )
            for hit in resp["hits"]["hits"]
        ]

    def delete(self) -> None:
        if self._client.indices.exists(index=self._index):
            self._client.indices.delete(index=self._index)
