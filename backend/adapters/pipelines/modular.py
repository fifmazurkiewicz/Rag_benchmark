"""
Modular RAG pipeline: chunker → embedder → vector_store
                      → [query_transformer] → vector_search → [reranker] → LLM

All LLM calls go through OpenRouter. Model names follow OpenRouter convention:
  "anthropic/claude-haiku-4-5-20251001", "openai/gpt-4o-mini", etc.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from backend.config import (
    DEFAULT_LLM_MODEL,
    DEFAULT_EMBEDDER_MODEL,
    DEFAULT_TOP_K,
    DEFAULT_MAX_TOKENS,
    RETRIEVE_K_MULTIPLIER,
)
from backend.registry import register
from backend.interfaces import Document, Chunk, PipelineResult, IngestStats

logger = logging.getLogger(__name__)


@register("pipeline", "qdrant_dense")
@register("pipeline", "qdrant_hybrid")
@register("pipeline", "chroma_dense")
@register("pipeline", "neo4j_dense")
class ModularPipeline:
    _PIPELINE_DEFAULTS: dict[str, dict[str, str]] = {
        "qdrant_dense":  {"vector_store": "qdrant",  "retrieval": "dense"},
        "qdrant_hybrid": {"vector_store": "qdrant",  "retrieval": "hybrid"},
        "chroma_dense":  {"vector_store": "chroma",  "retrieval": "dense"},
        "neo4j_dense":   {"vector_store": "neo4j",   "retrieval": "dense"},
    }

    def __init__(self, config: dict[str, Any]):
        from backend.factory import build_chunker, build_embedder
        from backend.registry import build as reg_build

        pipeline_name = config["pipeline"]
        cfg = {**self._PIPELINE_DEFAULTS.get(pipeline_name, {}), **config}

        self._chunker          = build_chunker(cfg.get("chunker", "fixed"), cfg)
        self._embedder         = build_embedder(cfg.get("embedder_model", DEFAULT_EMBEDDER_MODEL), cfg)
        self._store            = reg_build("vector_store", cfg.get("vector_store", "qdrant"), cfg)
        self._query_transformer = reg_build("query_transformer", cfg.get("query_transformer", "none"), cfg)
        self._reranker         = reg_build("reranker", cfg.get("reranker", "none"), cfg)
        self._llm_model        = cfg.get("llm_model", DEFAULT_LLM_MODEL)
        self._top_k            = int(cfg.get("top_k", DEFAULT_TOP_K))
        self._api_key          = cfg.get("openrouter_api_key")

        raw_retrieve_k    = int(cfg.get("retrieve_k", 0))
        self._retrieve_k  = raw_retrieve_k if raw_retrieve_k > 0 else self._top_k * RETRIEVE_K_MULTIPLIER

        self._llm_client = None
        logger.debug("ModularPipeline ready: pipeline=%s chunker=%s embedder=%s reranker=%s",
                     pipeline_name, cfg.get("chunker"), cfg.get("embedder_model"), cfg.get("reranker"))

    def _get_llm_client(self):
        if self._llm_client is None:
            from backend.services.openrouter_client import create_openrouter_client
            self._llm_client = create_openrouter_client(self._api_key)
        return self._llm_client

    def _generate_answer(self, question: str, chunks: list[Chunk]) -> tuple[str, int]:
        context = "\n\n".join(f"[{i+1}] {c.text}" for i, c in enumerate(chunks))
        prompt = (
            "Answer the question based only on the provided context.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n\nAnswer:"
        )
        response = self._get_llm_client().chat.completions.create(
            model=self._llm_model,
            max_tokens=DEFAULT_MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        text   = response.choices[0].message.content or ""
        tokens = response.usage.total_tokens if response.usage else 0
        return text, tokens

    async def ingest(self, docs: list[Document]) -> IngestStats:
        t0 = time.perf_counter()
        all_chunks: list[Chunk] = []
        for doc in docs:
            all_chunks.extend(self._chunker.chunk(doc))

        precomputed = [c.metadata.get("_precomputed_embedding") for c in all_chunks]
        if all(v is not None for v in precomputed):
            logger.debug("Using precomputed embeddings (late_chunking) for %d chunks", len(all_chunks))
            vectors = precomputed  # type: ignore[assignment]
        else:
            vectors = self._embedder.embed([c.text for c in all_chunks])

        self._store.upsert(all_chunks, vectors)
        elapsed = (time.perf_counter() - t0) * 1000
        logger.info("Ingest done: docs=%d chunks=%d latency=%.0fms", len(docs), len(all_chunks), elapsed)
        return IngestStats(doc_count=len(docs), chunk_count=len(all_chunks), duration_ms=elapsed)

    async def query(self, question: str, top_k: int = 0) -> PipelineResult:
        t0 = time.perf_counter()
        effective_top_k = top_k or self._top_k

        retrieval_query = self._query_transformer.transform(question)
        query_vec       = self._embedder.embed_query(retrieval_query)
        candidates      = self._store.search(query_vec, self._retrieve_k)
        chunks          = self._reranker.rerank(question, candidates, effective_top_k)
        answer, tokens  = self._generate_answer(question, chunks)

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
