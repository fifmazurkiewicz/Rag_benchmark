from __future__ import annotations
import time
from typing import Any
from backend.registry import register
from backend.interfaces import Document, Chunk, PipelineResult, IngestStats


@register("pipeline", "qdrant_dense")
@register("pipeline", "qdrant_hybrid")
@register("pipeline", "chroma_dense")
@register("pipeline", "elasticsearch_dense")
class ModularPipeline:
    """
    Pluggable pipeline: chunker → embedder → vector_store → LLM.
    The pipeline name determines the default vector_store, but config can override.
    """

    _PIPELINE_DEFAULTS = {
        "qdrant_dense":         {"vector_store": "qdrant",         "retrieval": "dense"},
        "qdrant_hybrid":        {"vector_store": "qdrant",         "retrieval": "hybrid"},
        "chroma_dense":         {"vector_store": "chroma",         "retrieval": "dense"},
        "elasticsearch_dense":  {"vector_store": "elasticsearch",  "retrieval": "dense"},
    }

    def __init__(self, config: dict[str, Any]):
        from backend.factory import build_chunker, build_embedder
        from backend.registry import build as reg_build

        pipeline_name = config["pipeline"]
        defaults = self._PIPELINE_DEFAULTS.get(pipeline_name, {})
        cfg = {**defaults, **config}

        self._chunker = build_chunker(cfg.get("chunker", "fixed"), cfg)
        self._embedder = build_embedder(cfg.get("embedder_model", "openai/text-embedding-3-small"), cfg)
        self._store = reg_build("vector_store", cfg.get("vector_store", "qdrant"), cfg)
        self._reranker = reg_build("reranker", cfg.get("reranker", "none"), cfg)
        self._retrieval = cfg.get("retrieval", "dense")
        self._llm_model = cfg.get("llm_model", "claude-haiku-4-5-20251001")
        self._top_k = int(cfg.get("top_k", 5))
        # retrieve more candidates before reranking, then trim to top_k
        self._retrieve_k = int(cfg.get("retrieve_k", self._top_k * 4))
        self._llm_client = None

    def _get_llm(self):
        if self._llm_client is None:
            import anthropic
            self._llm_client = anthropic.Anthropic()
        return self._llm_client

    def _generate(self, question: str, chunks: list[Chunk]) -> tuple[str, int]:
        context = "\n\n".join(f"[{i+1}] {c.text}" for i, c in enumerate(chunks))
        prompt = (
            f"Answer the question based on the provided context.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n\nAnswer:"
        )
        client = self._get_llm()
        response = client.messages.create(
            model=self._llm_model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text, response.usage.input_tokens + response.usage.output_tokens

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
        query_vec = self._embedder.embed_query(question)
        candidates = self._store.search(query_vec, self._retrieve_k)
        chunks = self._reranker.rerank(question, candidates, effective_top_k)
        answer, tokens = self._generate(question, chunks)
        return PipelineResult(
            answer=answer,
            source_chunks=chunks,
            latency_ms=(time.perf_counter() - t0) * 1000,
            tokens_used=tokens,
        )

    async def teardown(self) -> None:
        if hasattr(self._store, "delete"):
            self._store.delete()
