"""
Neo4j GraphRAG pipeline.

Approach:
  1. Ingest: extract entities + relations via LLM → store as Neo4j nodes/edges
  2. Query:  vector search finds seed nodes, Cypher traversal expands context,
             LLM synthesises the answer

Compared to FalkorDB GraphRAG SDK (which wraps everything),
this adapter gives full control over Cypher and graph schema.
"""
from __future__ import annotations
import logging
import time
from typing import Any
from backend.config import DEFAULT_LLM_MODEL, DEFAULT_EMBEDDER_MODEL, DEFAULT_MAX_TOKENS
from backend.registry import register
from backend.interfaces import Document, Chunk, PipelineResult, IngestStats

logger = logging.getLogger(__name__)

_EXTRACT_SYSTEM = """Extract entities and relationships from the text.
Return JSON: {"entities": [{"name": str, "type": str, "desc": str}],
              "relations": [{"source": str, "rel": str, "target": str}]}
Only return JSON, no other text."""


@register("pipeline", "neo4j_graphrag")
class Neo4jGraphRAGPipeline:

    def __init__(self, config: dict[str, Any]):
        from neo4j import GraphDatabase

        self._uri            = config.get("neo4j_uri", "bolt://localhost:7687")
        self._user           = config.get("neo4j_user", "neo4j")
        self._password       = config.get("neo4j_password", "password")
        self._llm_model      = config.get("llm_model", DEFAULT_LLM_MODEL)
        self._embedder_model = config.get("embedder_model", DEFAULT_EMBEDDER_MODEL)
        self._api_key        = config.get("openrouter_api_key")
        self._dim            = int(config.get("embedding_dim", 1536))
        self._driver         = GraphDatabase.driver(self._uri, auth=(self._user, self._password))
        self._llm            = None
        self._embedder       = None
        self._ensure_schema()

    def _get_llm(self):
        if self._llm is None:
            from backend.services.openrouter_client import create_openrouter_client
            self._llm = create_openrouter_client(self._api_key)
        return self._llm

    def _get_embedder(self):
        if self._embedder is None:
            from backend.factory import build_embedder
            self._embedder = build_embedder(self._embedder_model, {"model": self._embedder_model})
        return self._embedder

    def _ensure_schema(self):
        with self._driver.session() as s:
            s.run("CREATE CONSTRAINT entity_name IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE")
            s.run(
                "CREATE VECTOR INDEX chunk_vec IF NOT EXISTS "
                "FOR (c:Chunk) ON c.embedding "
                "OPTIONS {indexConfig: {`vector.dimensions`: $dim, `vector.similarity_function`: 'cosine'}}",
                dim=self._dim,
            )

    def _extract(self, text: str) -> dict:
        import json, re
        response = self._get_llm().chat.completions.create(
            model=self._llm_model,
            max_tokens=DEFAULT_MAX_TOKENS,
            messages=[
                {"role": "system", "content": _EXTRACT_SYSTEM},
                {"role": "user",   "content": text[:3000]},
            ],
        )
        raw = response.choices[0].message.content or ""
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        try:
            return json.loads(m.group()) if m else {"entities": [], "relations": []}
        except Exception:
            return {"entities": [], "relations": []}

    async def ingest(self, docs: list[Document]) -> IngestStats:
        t0 = time.perf_counter()
        embedder = self._get_embedder()

        for doc in docs:
            extracted = self._extract(doc.text)
            vec = embedder.embed_query(doc.text)

            with self._driver.session() as s:
                s.run(
                    "MERGE (c:Chunk {id: $id}) SET c.text=$text, c.doc_id=$doc_id, c.embedding=$vec",
                    id=doc.id, text=doc.text[:2000], doc_id=doc.id, vec=vec,
                )
                for ent in extracted.get("entities", []):
                    s.run(
                        "MERGE (e:Entity {name: $name}) SET e.type=$type, e.desc=$desc",
                        name=ent.get("name", ""), type=ent.get("type", ""), desc=ent.get("desc", ""),
                    )
                    s.run(
                        "MATCH (c:Chunk {id:$cid}), (e:Entity {name:$name}) MERGE (c)-[:MENTIONS]->(e)",
                        cid=doc.id, name=ent.get("name", ""),
                    )
                for rel in extracted.get("relations", []):
                    rel_type = rel.get("rel", "RELATED_TO").upper().replace(" ", "_")
                    s.run(
                        f"MATCH (a:Entity {{name:$src}}), (b:Entity {{name:$tgt}}) "
                        f"MERGE (a)-[:{rel_type}]->(b)",
                        src=rel.get("source", ""), tgt=rel.get("target", ""),
                    )

        elapsed = (time.perf_counter() - t0) * 1000
        logger.info("Neo4j ingest done: docs=%d latency=%.0fms", len(docs), elapsed)
        return IngestStats(doc_count=len(docs), duration_ms=elapsed)

    async def query(self, question: str, top_k: int = 5) -> PipelineResult:
        t0 = time.perf_counter()
        embedder = self._get_embedder()
        q_vec = embedder.embed_query(question)

        with self._driver.session() as s:
            seed = s.run(
                """
                CALL db.index.vector.queryNodes('chunk_vec', $k, $vec)
                YIELD node, score
                RETURN node.id AS id, node.text AS text, score
                """,
                k=top_k, vec=q_vec,
            ).data()

            chunk_ids = [r["id"] for r in seed]
            graph_ctx = s.run(
                """
                MATCH (c:Chunk)-[:MENTIONS]->(e:Entity)
                WHERE c.id IN $ids
                OPTIONAL MATCH (e)-[r]-(neighbour:Entity)
                RETURN e.name AS entity, e.type AS type, e.desc AS desc,
                       collect(DISTINCT neighbour.name)[..5] AS neighbours
                LIMIT 30
                """,
                ids=chunk_ids,
            ).data()

        chunks = [
            Chunk(id=r["id"], doc_id="", text=r["text"], index=i, metadata={"score": r["score"]})
            for i, r in enumerate(seed)
        ]

        graph_summary = "\n".join(
            f"- {r['entity']} ({r['type']}): {r['desc']} | related: {', '.join(r['neighbours'])}"
            for r in graph_ctx
        )
        context = "\n\n".join(c.text for c in chunks)
        prompt = (
            f"Knowledge graph context:\n{graph_summary}\n\n"
            f"Document chunks:\n{context}\n\n"
            f"Question: {question}\nAnswer:"
        )
        response = self._get_llm().chat.completions.create(
            model=self._llm_model,
            max_tokens=DEFAULT_MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        answer = response.choices[0].message.content or ""
        tokens = response.usage.total_tokens if response.usage else 0

        return PipelineResult(
            answer=answer,
            source_chunks=chunks,
            latency_ms=(time.perf_counter() - t0) * 1000,
            tokens_used=tokens,
            metadata={"graph_entities": len(graph_ctx)},
        )

    async def teardown(self) -> None:
        self._driver.close()
