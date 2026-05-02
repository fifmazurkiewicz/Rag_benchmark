"""
Modular RAG pipeline: chunker → embedder → vector_store → [query_transformer] →
                      vector_search → [reranker] → LLM (via OpenRouter)

All LLM calls go through OpenRouter (OPENROUTER_API_KEY).
Model names follow OpenRouter convention: "anthropic/claude-haiku-4-5-20251001".
"""
from __future__ import annotations

import os
import time
from typing import Any

from backend.registry import register
from backend.interfaces import Document, Chunk, PipelineResult, IngestStats

_OPENROUTER_BASE = "https://openrouter.ai/api/v1"


@register("pipeline", "qdrant_dense")
@register("pipeline", "qdrant_hybrid")
@register("pipeline", "chroma_dense")
@register("pipeline", "neo4j_dense")
class ModularPipeline:
    _PIPELINE_DEFAULTS = {
        "qdrant_dense":  {"vector_store": "qdrant",  "retrieval": "dense"},
        "qdrant_hybrid": {"vector_store": "qdrant",  "retrieval": "hybrid"},
        "chroma_dense":  {"vector_store": "chroma",  "retrieval": "dense"},
        "neo4j_dense":   {"vector_store": "neo4j",   "retrieval": "dense"},
    }

    def __init__(self, config: dict[str, Any]):
        from backend.factory import build_chunker, build_embedder
        from backend.registry import build as reg_build

        pipeline_name = config["pipeline"]
        defaults = self._PIPELINE_DEFAULTS.get(pipeline_name, {})
        cfg = {**defaults, **config}

        self._chunker = build_chunker(cfg.get("chunker", "fixed"), cfg)
        self._embedder = build_embedder(cfg.get("embedder_model", "openrouter/text-embedding-3-small"), cfg)
        self._store = reg_build("vector_store", cfg.get("vector_store", "qdrant"), cfg)
        self._query_transformer = reg_build("query_transformer", cfg.get("query_transformer", "none"), cfg)
        self._reranker = reg_build("reranker", cfg.get("reranker", "none"), cfg)
        self._retrieval = cfg.get("retrieval", "dense")
        self._llm_model = cfg.get("llm_model", "anthropic/claude-haiku-4-5-20251001")
        self._top_k = int(cfg.get("top_k", 5))
        self._retrieve_k = int(cfg.get("retrieve_k", self._top_k * 4))
        self._llm_client = None
        self._api_key = cfg.get("openrouter_api_key") or os.environ.get("OPENROUTER_API_KEY", "")

    def _get_llm(self):
        if self._llm_client is None:
            import openai
            self._llm_client = openai.OpenAI(
                api_key=self._api_key,
                base_url=_OPENROUTER_BASE,
                default_headers={
                    "HTTP-Referer": "https://github.com/fifmazurkiewicz/Rag_benchmark",
                    "X-Title": "RAG Benchmark",
                },
            )
        return self._llm_client

    def _generate(self, question: str, chunks: list[Chunk]) -> tuple[str, int]:
        context = "\n\n".join(f"[{i+1}] {c.text}" for i, c in enumerate(chunks))
        prompt = (
            f"Answer the question based only on the provided context.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n\nAnswer:"
        )
        response = self._get_llm().chat.completions.create(
            model=self._llm_model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.choices[0].message.content or ""
        tokens = response.usage.total_tokens if response.usage else 0
        return text, tokens

    async def ingest(self, docs: list[Document]) -> IngestStats:
        t0 = time.perf_counter()
        all_chunks: list[Chunk] = []
        for doc in docs:
            all_chunks.extend(self._chunker.chunk(doc))

        texts = [c.text for c in all_chunks]
        vectors = self._embedder.embed(texts)
        self._store.upsert(all_chunks, vectors)

        return IngestStats(
            doc_count=len(docs),
            chunk_count=len(all_chunks),
            duration_ms=(time.perf_counter() - t0) * 1000,
        )

    async def query(self, question: str, top_k: int = 5) -> PipelineResult:
        t0 = time.perf_counter()
        effective_top_k = top_k or self._top_k

        retrieval_query = self._query_transformer.transform(question)
        query_vec = self._embedder.embed_query(retrieval_query)
        candidates = self._store.search(query_vec, self._retrieve_k)
        # reranker always scores against original question, not HyDE passage
        chunks = self._reranker.rerank(question, candidates, effective_top_k)
        answer, tokens = self._generate(question, chunks)

        meta: dict[str, Any] = {}
        if retrieval_query != question:
            meta["retrieval_query"] = retrieval_query

        return PipelineResult(
            answer=answer,
            source_chunks=chunks,
            latency_ms=(time.perf_counter() - t0) * 1000,
            tokens_used=tokens,
            metadata=meta,
        )

    async def teardown(self) -> None:
        if hasattr(self._store, "delete"):
            self._store.delete()
