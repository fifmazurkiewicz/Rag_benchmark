from __future__ import annotations
from typing import Any
from backend.registry import register
from backend.interfaces import Chunk


@register("vector_store", "neo4j")
class Neo4jVectorStore:
    """
    Neo4j as a vector store using native vector index (Neo4j 5.x+).
    Nodes: (:Chunk {id, doc_id, text, index}) with 'embedding' property.
    """

    def __init__(self, config: dict[str, Any]):
        from neo4j import GraphDatabase
        self._uri = config.get("neo4j_uri", "bolt://localhost:7687")
        self._user = config.get("neo4j_user", "neo4j")
        self._password = config.get("neo4j_password", "password")
        self._index = config.get("collection_name", "rag_bench")
        self._dim = int(config.get("embedding_dim", 1536))
        self._driver = GraphDatabase.driver(self._uri, auth=(self._user, self._password))
        self._ensure_index()

    def _ensure_index(self):
        with self._driver.session() as s:
            s.run(
                "CREATE VECTOR INDEX $name IF NOT EXISTS "
                "FOR (c:Chunk) ON c.embedding "
                "OPTIONS {indexConfig: {`vector.dimensions`: $dim, `vector.similarity_function`: 'cosine'}}",
                name=self._index,
                dim=self._dim,
            )

    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        with self._driver.session() as s:
            s.run(
                """
                UNWIND $rows AS row
                MERGE (c:Chunk {id: row.id})
                SET c.doc_id   = row.doc_id,
                    c.text     = row.text,
                    c.index    = row.index,
                    c.embedding = row.embedding
                """,
                rows=[
                    {"id": ch.id, "doc_id": ch.doc_id, "text": ch.text,
                     "index": ch.index, "embedding": vec}
                    for ch, vec in zip(chunks, vectors)
                ],
            )

    def search(self, query_vec: list[float], top_k: int) -> list[Chunk]:
        with self._driver.session() as s:
            result = s.run(
                """
                CALL db.index.vector.queryNodes($index, $k, $vec)
                YIELD node, score
                RETURN node.id AS id, node.doc_id AS doc_id,
                       node.text AS text, node.index AS idx, score
                """,
                index=self._index,
                k=top_k,
                vec=query_vec,
            )
            return [
                Chunk(
                    id=r["id"],
                    doc_id=r["doc_id"],
                    text=r["text"],
                    index=r["idx"],
                    metadata={"score": r["score"]},
                )
                for r in result
            ]

    def delete(self) -> None:
        with self._driver.session() as s:
            s.run("MATCH (c:Chunk) DETACH DELETE c")
        self._driver.close()
