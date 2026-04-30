from __future__ import annotations
import time
from typing import Any
from backend.registry import register
from backend.interfaces import Document, Chunk, PipelineResult, IngestStats


@register("pipeline", "falkordb_graphrag")
class FalkorDBGraphRAGPipeline:
    """
    Monolithic GraphRAG pipeline backed by FalkorDB.
    Does not use the separate chunker/embedder/vector_store adapters —
    FalkorDB SDK handles ingestion and retrieval internally.
    """

    def __init__(self, config: dict[str, Any]):
        self._host = config.get("falkordb_host", "localhost")
        self._graph_name = config.get("graph_name", "rag_bench")
        self._llm_model = config.get("llm_model", "openai/gpt-4o-mini")
        self._embedder_model = config.get("embedder_model", "openai/text-embedding-3-large")
        self._rag = None

    def _build_rag(self):
        from graphrag_sdk import GraphRAG, ConnectionConfig, LiteLLM, LiteLLMEmbedder
        return GraphRAG(
            connection=ConnectionConfig(host=self._host, graph_name=self._graph_name),
            llm=LiteLLM(model=self._llm_model),
            embedder=LiteLLMEmbedder(model=self._embedder_model),
        )

    async def ingest(self, docs: list[Document]) -> IngestStats:
        t0 = time.perf_counter()
        rag = self._build_rag()
        async with rag:
            for doc in docs:
                await rag.ingest(text=doc.text, document_id=doc.id)
            await rag.finalize()
        return IngestStats(
            doc_count=len(docs),
            duration_ms=(time.perf_counter() - t0) * 1000,
            metadata={"note": "chunk_count not available — FalkorDB SDK manages chunking internally"},
        )

    async def query(self, question: str, top_k: int = 5) -> PipelineResult:
        t0 = time.perf_counter()
        rag = self._build_rag()
        async with rag:
            result = await rag.completion(question, return_context=True)

        source_chunks = [
            Chunk(
                id=f"falkor_{i}",
                doc_id=getattr(ctx, "document_id", ""),
                text=getattr(ctx, "text", str(ctx)),
                index=i,
                metadata={"source": "falkordb_graphrag"},
            )
            for i, ctx in enumerate(getattr(result, "context", []))
        ]
        return PipelineResult(
            answer=result.answer if hasattr(result, "answer") else str(result),
            source_chunks=source_chunks,
            latency_ms=(time.perf_counter() - t0) * 1000,
            tokens_used=getattr(getattr(result, "usage", None), "total_tokens", 0),
            metadata={"graph_name": self._graph_name},
        )

    async def teardown(self) -> None:
        pass
