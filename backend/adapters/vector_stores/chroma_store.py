from __future__ import annotations
from typing import Any
from backend.registry import register
from backend.interfaces import Chunk


@register("vector_store", "chroma")
class ChromaVectorStore:
    def __init__(self, config: dict[str, Any]):
        import chromadb
        path = config.get("chroma_path", "./chroma_data")
        self._collection_name = config.get("collection_name", "rag_bench")
        self._client = chromadb.PersistentClient(path=path)
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        self._collection.upsert(
            ids=[c.id for c in chunks],
            embeddings=vectors,
            documents=[c.text for c in chunks],
            metadatas=[{"doc_id": c.doc_id, "index": c.index, **c.metadata} for c in chunks],
        )

    def search(self, query_vec: list[float], top_k: int) -> list[Chunk]:
        results = self._collection.query(
            query_embeddings=[query_vec],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        chunks = []
        for chunk_id, doc, meta, dist in zip(
            results["ids"][0],
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            chunks.append(Chunk(
                id=chunk_id,
                doc_id=meta.get("doc_id", ""),
                text=doc,
                index=meta.get("index", 0),
                metadata={"score": 1 - dist},
            ))
        return chunks

    def delete(self) -> None:
        self._client.delete_collection(self._collection_name)
