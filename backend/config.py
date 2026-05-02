"""Shared constants — single source of truth for all magic strings and numbers."""
from __future__ import annotations

# ── OpenRouter ────────────────────────────────────────────────────────────────
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_REFERER  = "https://github.com/fifmazurkiewicz/Rag_benchmark"
OPENROUTER_TITLE    = "RAG Benchmark"

# ── Default models ────────────────────────────────────────────────────────────
DEFAULT_LLM_MODEL      = "anthropic/claude-haiku-4-5-20251001"
DEFAULT_EMBEDDER_MODEL = "openrouter/text-embedding-3-small"
DEFAULT_RERANKER_MODEL = "anthropic/claude-haiku-4-5-20251001"
DEFAULT_HYDE_MODEL     = "anthropic/claude-haiku-4-5-20251001"

# ── Pipeline defaults ─────────────────────────────────────────────────────────
DEFAULT_CHUNK_SIZE        = 512
DEFAULT_OVERLAP           = 64
DEFAULT_TOP_K             = 5
RETRIEVE_K_MULTIPLIER     = 4   # retrieve_k = top_k * this when retrieve_k == 0
DEFAULT_MAX_TOKENS        = 1024
DEFAULT_HYDE_MAX_TOKENS   = 256
DEFAULT_RERANKER_MAX_TOKENS = 256

# ── Chunking ──────────────────────────────────────────────────────────────────
DEFAULT_SIMILARITY_THRESHOLD = 0.75
DEFAULT_LATE_CHUNKING_MODEL  = "BAAI/bge-m3"
LATE_CHUNKING_MAX_TOKENS     = 8192

# ── Pipeline type classification ──────────────────────────────────────────────
GRAPH_PIPELINE_TYPES = frozenset({"falkordb_graphrag", "neo4j_graphrag"})
MODULAR_PIPELINE_TYPES = frozenset({"qdrant_dense", "qdrant_hybrid", "chroma_dense", "neo4j_dense"})
