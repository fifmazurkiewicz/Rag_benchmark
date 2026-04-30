"""
Obsidian Second Brain RAG Pipeline — Karpathy-style.

Core idea:
  1. Ingest vault notes with the ObsidianChunker
  2. Build an in-memory wikilink graph (or push to Neo4j/FalkorDB)
  3. At query time:
       a. Semantic search → seed notes
       b. Graph expansion: follow outlinks + backlinks 1 hop
       c. Re-rank expanded context by relevance
       d. LLM generates answer citing note titles
"""
from __future__ import annotations
import time
from typing import Any
from backend.registry import register
from backend.interfaces import Document, Chunk, PipelineResult, IngestStats


@register("pipeline", "obsidian_rag")
class ObsidianRAGPipeline:

    def __init__(self, config: dict[str, Any]):
        from backend.factory import build_embedder
        import anthropic

        self._embedder_model = config.get("embedder_model", "openai/text-embedding-3-small")
        self._llm_model      = config.get("llm_model", "claude-haiku-4-5-20251001")
        self._top_k          = int(config.get("top_k", 5))
        self._graph_hops     = int(config.get("graph_hops", 1))  # how far to follow links
        self._embedder       = build_embedder(self._embedder_model, config)
        self._llm            = anthropic.Anthropic()

        # In-memory stores (populated at ingest)
        self._chunks:     list[Chunk]         = []
        self._vectors:    list[list[float]]   = []
        self._note_index: dict[str, list[int]] = {}  # doc_id → chunk indices
        self._link_graph: dict[str, list[str]] = {}  # doc_id → [linked doc_ids]

    def _cosine(self, a: list[float], b: list[float]) -> float:
        dot  = sum(x * y for x, y in zip(a, b))
        na   = sum(x * x for x in a) ** 0.5
        nb   = sum(x * x for x in b) ** 0.5
        return dot / (na * nb) if na and nb else 0.0

    async def ingest(self, docs: list[Document]) -> IngestStats:
        from backend.adapters.chunkers.obsidian import ObsidianChunker
        t0      = time.perf_counter()
        chunker = ObsidianChunker({"chunk_size": 400, "split_depth": 2})

        all_chunks: list[Chunk] = []
        for doc in docs:
            chunks = chunker.chunk(doc)
            start  = len(all_chunks)
            all_chunks.extend(chunks)
            self._note_index[doc.id] = list(range(start, start + len(chunks)))
            # Rebuild link graph from metadata
            self._link_graph[doc.id] = doc.metadata.get("outlink_ids", [])

        texts   = [c.text for c in all_chunks]
        vectors = self._embedder.embed(texts)

        self._chunks  = all_chunks
        self._vectors = vectors

        return IngestStats(
            doc_count=len(docs),
            chunk_count=len(all_chunks),
            duration_ms=(time.perf_counter() - t0) * 1000,
        )

    def _expand_via_graph(self, seed_doc_ids: set[str], hops: int) -> set[str]:
        """Follow wikilinks outward and inward up to `hops` steps."""
        frontier  = set(seed_doc_ids)
        expanded  = set(seed_doc_ids)
        for _ in range(hops):
            next_frontier: set[str] = set()
            for doc_id in frontier:
                for linked in self._link_graph.get(doc_id, []):
                    if linked not in expanded:
                        next_frontier.add(linked)
                        expanded.add(linked)
            frontier = next_frontier
        return expanded

    async def query(self, question: str, top_k: int = 5) -> PipelineResult:
        t0      = time.perf_counter()
        k       = top_k or self._top_k
        q_vec   = self._embedder.embed_query(question)

        # Step 1: score all chunks by cosine similarity
        scored = sorted(
            enumerate(self._vectors),
            key=lambda iv: self._cosine(q_vec, iv[1]),
            reverse=True,
        )
        seed_indices = [i for i, _ in scored[:k]]
        seed_doc_ids = {self._chunks[i].doc_id for i in seed_indices}

        # Step 2: graph expansion — follow wikilinks
        expanded_doc_ids = self._expand_via_graph(seed_doc_ids, self._graph_hops)

        # Step 3: gather all chunks from expanded notes, re-rank
        candidate_indices = [
            i for doc_id in expanded_doc_ids
            for i in self._note_index.get(doc_id, [])
        ]
        reranked = sorted(
            candidate_indices,
            key=lambda i: self._cosine(q_vec, self._vectors[i]),
            reverse=True,
        )[:k * 2]

        final_chunks = [self._chunks[i] for i in reranked]

        # Step 4: build context with note titles
        def _fmt(c: Chunk) -> str:
            title = c.metadata.get("title", c.doc_id)
            return f"[{title}]\n{c.text}"

        context = "\n\n---\n\n".join(_fmt(c) for c in final_chunks)
        prompt  = (
            "You are querying a personal knowledge base (Obsidian vault).\n"
            "Answer the question using only the notes below. "
            "Cite note titles like [Note Title] when referencing them.\n\n"
            f"Notes:\n{context}\n\n"
            f"Question: {question}\nAnswer:"
        )
        resp   = self._llm.messages.create(
            model=self._llm_model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        answer = resp.content[0].text
        tokens = resp.usage.input_tokens + resp.usage.output_tokens

        return PipelineResult(
            answer=answer,
            source_chunks=final_chunks,
            latency_ms=(time.perf_counter() - t0) * 1000,
            tokens_used=tokens,
            metadata={
                "seed_notes":    len(seed_doc_ids),
                "expanded_notes": len(expanded_doc_ids),
                "graph_hops":    self._graph_hops,
            },
        )

    async def teardown(self) -> None:
        self._chunks  = []
        self._vectors = []
        self._note_index.clear()
        self._link_graph.clear()
