# RAG Benchmark

A modular platform for benchmarking Retrieval-Augmented Generation (RAG) pipelines. Compare vector databases, chunking strategies, embedding models, rerankers, and query techniques against each other on the same dataset — one leaderboard, reproducible results.

## What it does

- Run multiple RAG pipeline configurations against the same dataset and compare quality metrics
- Every component is swappable via config: chunker, embedder, vector store, reranker, query transformer
- Results cached by config hash — identical experiments never run twice
- Export results to Excel for offline analysis
- Datasets: FinQA, MedQA, Wikipedia, PubMed, Polish bank fee schedules (TOiP), Obsidian vaults

---

## Quick start

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env — set OPENROUTER_API_KEY

# 2. Start all services
docker compose up -d

# 3. Open the UI
open http://localhost:5173
```

**The only required API key is `OPENROUTER_API_KEY`** — all LLM, embedding, and reranking calls go through [OpenRouter](https://openrouter.ai).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│  Experiments · Datasets · Leaderboard · Dashboard · Run     │
└──────────────────────┬──────────────────────────────────────┘
                       │ REST + WebSocket
┌──────────────────────▼──────────────────────────────────────┐
│                      Backend (FastAPI)                       │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐  │
│   │                   Registry                          │  │
│   │   @register("chunker" | "embedder" | "reranker"    │  │
│   │             | "pipeline" | "query_transformer")    │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                             │
│   RAG Pipeline:                                             │
│   Document → Chunker → Embedder → VectorStore              │
│                              ↓                              │
│   Query → QueryTransformer → Embedder → VectorSearch       │
│                              → Reranker → LLM → Answer     │
└──────────────────────────────────────────────────────────────┘
         │         │          │          │
      Qdrant    Chroma      Neo4j    FalkorDB
```

All LLM generation, embedding, and reranking go through **OpenRouter** (`openai` SDK, `base_url=https://openrouter.ai/api/v1`). Model names follow the OpenRouter convention: `"anthropic/claude-haiku-4-5-20251001"`, `"openai/gpt-4o-mini"`, etc.

---

## Services

| Service | Port | Purpose |
|---|---|---|
| Frontend | 5173 | React UI |
| Backend | 8000 | FastAPI + WebSocket |
| Qdrant | 6333 | Vector search (primary) |
| Chroma | 8001 | Vector search (alternative) |
| Neo4j | 7474 / 7687 | Graph RAG + vector index |
| FalkorDB | 6379 / 3000 | GraphRAG SDK |

---

## Components

### Chunkers

| Name | Description | Key config |
|---|---|---|
| `fixed` | Sliding window by word count | `chunk_size`, `overlap` |
| `sentence` | Groups N sentences together | `sentences_per_chunk`, `overlap_sentences` |
| `recursive` | Hierarchical split: `\n\n` → `\n` → `. ` → char | `chunk_size`, `overlap` |
| `semantic` | Splits when cosine similarity drops between sentences | `similarity_threshold` |
| `markdown` | Splits on H1-H6 headings | `chunk_size` |
| `late_chunking` | Encode full document first (BAAI/bge-m3), then split token embeddings — each chunk vector carries full-document context. Pipeline skips re-embedding automatically. | `chunk_size`, `late_chunking_model` |
| `propositional` | LLM decomposes text into atomic propositions | `llm_model` |
| `obsidian` | Heading-aware + `[[wikilink]]` backlink context | `vault_path` |

### Embedders

| Name | Dimensions | Provider |
|---|---|---|
| `openrouter/text-embedding-3-small` | 1536 | OpenRouter → OpenAI |
| `openrouter/text-embedding-3-large` | 3072 | OpenRouter → OpenAI |
| `openrouter/text-embedding-ada-002` | 1536 | OpenRouter → OpenAI |
| `hf/bge-large-en` | 1024 | Local (sentence-transformers) |
| `hf/all-MiniLM-L6-v2` | 384 | Local (sentence-transformers) |
| `hf/multilingual-e5-large` | 1024 | Local (sentence-transformers) |

### Vector stores

| Name | Backend | Notes |
|---|---|---|
| `qdrant` | Qdrant | COSINE distance, auto-creates collection |
| `chroma` | ChromaDB | Persistent SQLite |
| `neo4j` | Neo4j 5.x | Native vector index |

### Pipelines

| Name | Type | Reranker | Query transformer | Description |
|---|---|---|---|---|
| `qdrant_dense` | Modular | ✅ | ✅ | Dense retrieval → Qdrant |
| `qdrant_hybrid` | Modular | ✅ | ✅ | Hybrid (dense + sparse) → Qdrant |
| `chroma_dense` | Modular | ✅ | ✅ | Dense retrieval → Chroma |
| `neo4j_dense` | Modular | ✅ | ✅ | Dense retrieval → Neo4j |
| `neo4j_graphrag` | Graph | — | — | Entity extraction + graph traversal |
| `falkordb_graphrag` | Graph | — | — | FalkorDB GraphRAG SDK (monolithic) |
| `obsidian_rag` | Obsidian | — | — | Vault-aware + wikilink graph expansion |

Pipelines are intentionally elastic — graph pipelines don't need a reranker or query transformer and simply don't implement those hooks.

### Query transformers

| Name | Description |
|---|---|
| `none` | Passthrough — original query goes to retrieval |
| `hyde` | Generates hypothetical answer first, embeds that instead ([HyDE docs](docs/hyde.md)) |

### Rerankers

| Name | Approach | Notes |
|---|---|---|
| `none` | Passthrough | Baseline |
| `cross_encoder` | Local cross-encoder (ms-marco-MiniLM-L-6-v2) | CPU, ~100ms/20 candidates |
| `openrouter` | LLM listwise ranking | One API call, any OpenRouter model |
| `cohere` | Cohere Rerank API | Multilingual, requires `COHERE_API_KEY` |

---

## Experiment configuration

An experiment compares multiple pipeline configurations on the same dataset.

```json
{
  "name": "toip_comparison",
  "dataset": "toip_banks",
  "description": "Compare HyDE vs plain retrieval on Polish bank fees",
  "metrics": ["faithfulness", "answer_relevancy", "context_recall", "hit_rate"],
  "pipelines": [
    {
      "name": "baseline",
      "pipeline": "qdrant_dense",
      "chunker": "markdown",
      "chunk_size": 512,
      "overlap": 64,
      "embedder_model": "openrouter/text-embedding-3-small",
      "llm_model": "anthropic/claude-haiku-4-5-20251001",
      "query_transformer": "none",
      "reranker": "none",
      "top_k": 5
    },
    {
      "name": "hyde_reranked",
      "pipeline": "qdrant_dense",
      "chunker": "markdown",
      "chunk_size": 512,
      "overlap": 64,
      "embedder_model": "openrouter/text-embedding-3-small",
      "llm_model": "anthropic/claude-haiku-4-5-20251001",
      "query_transformer": "hyde",
      "reranker": "cross_encoder",
      "top_k": 5,
      "retrieve_k": 20
    }
  ]
}
```

**`retrieve_k`**: number of candidates to fetch before reranking. `0` (default) means `top_k × 4` automatically. Set explicitly when using a reranker to control the reranking pool size — e.g. `top_k: 5, retrieve_k: 20` fetches 20 candidates and reranks down to 5.

```json
```

**Result caching**: experiments are fingerprinted by SHA-256 hash of `(dataset + pipeline configs + metrics)`. Running the same config twice returns the cached `run_id` instantly. Use `POST /experiments/{name}/run?force=true` to bypass.

---

## Metrics

| Metric | Library | What it measures |
|---|---|---|
| `faithfulness` | RAGAS | Is the answer grounded in the retrieved context? |
| `answer_relevancy` | RAGAS | Does the answer address the question? |
| `context_precision` | RAGAS | Are retrieved chunks relevant? |
| `context_recall` | RAGAS | Did retrieval find the needed information? |
| `answer_correctness` | RAGAS | Does the answer match ground truth? |
| `hallucination` | DeepEval | Did the model make up facts? |
| `hit_rate` | Built-in | Does ground truth appear in retrieved chunks? |
| `latency_p95` | Built-in | 95th percentile query latency in ms |

---

## Dataset sources

Datasets are prepared once and reused across experiments.

| Source | Domain | QA pairs | Notes |
|---|---|---|---|
| `finqa` | Finance | ~8K built-in | IBM FinQA, HuggingFace |
| `medqa` | Medicine | ~12K built-in | USMLE licensing exam |
| `medmcqa` | Medicine | ~194K built-in | 21 medical subjects |
| `wikipedia` | General | None (generate optionally) | Wikipedia API, no key needed |
| `pubmed` | Biomedicine | None (generate optionally) | NCBI E-utilities, 3 req/s free |
| `football` | Sports | None (generate optionally) | Wikipedia football/volleyball articles |
| `toip_banks` | Finance/Polish | None | Public PDFs from 10 Polish banks, Docling → Markdown |

### Build a dataset via UI

1. Go to **Datasets** page → select source → configure → click **Build**

### Build via API

```bash
curl -X POST http://localhost:8000/datasets/from-source \
  -H "Content-Type: application/json" \
  -d '{"source": "toip_banks", "dataset_name": "toip_2025", "config": {"segment": "individual"}}'
```

### Import Obsidian vault

```bash
curl -X POST http://localhost:8000/datasets/from-vault \
  -H "Content-Type: application/json" \
  -d '{"vault_path": "/path/to/vault", "dataset_name": "my_vault", "generate_qa": false}'
```

---

## Extending the platform

### Add a new chunker

Create `backend/adapters/chunkers/my_chunker.py`:

```python
import uuid
from typing import Any
from backend.registry import register
from backend.interfaces import Document, Chunk

@register("chunker", "my_chunker")
class MyChunker:
    def __init__(self, config: dict[str, Any]):
        self.size = int(config.get("chunk_size", 512))

    def chunk(self, doc: Document) -> list[Chunk]:
        pieces = my_split_logic(doc.text, self.size)
        return [
            Chunk(id=str(uuid.uuid4()), doc_id=doc.id, text=p, index=i,
                  metadata={"chunker": "my_chunker"})
            for i, p in enumerate(pieces)
        ]
```

Restart backend → `my_chunker` appears in the frontend dropdown. No other files need changes.

The same pattern applies to every component type. See [`CLAUDE.md`](CLAUDE.md) for full protocol reference.

---

## API reference

### Registry

```
GET /registry/                    → all components by type
GET /registry/{type}              → components of one type
```

### Datasets

```
GET  /datasets/                   → list datasets
POST /datasets/upload             → upload JSON file
POST /datasets/from-source        → build from registered source
POST /datasets/from-vault         → import Obsidian vault
DELETE /datasets/{name}           → delete dataset
GET  /datasets/sources/           → list available sources
GET  /datasets/vault/stats?vault_path=… → vault preview
```

### Experiments

```
GET  /experiments/                → list experiment names
POST /experiments/                → save experiment config
POST /experiments/{name}/run      → run (cached unless ?force=true)
GET  /experiments/runs/{run_id}   → live run status (polling)
GET  /experiments/results/        → list result IDs
GET  /experiments/results/{id}    → get result JSON
GET  /experiments/results/{id}/export → download .xlsx
WS   /ws/runs/{run_id}            → stream run status
```

---

## Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `OPENROUTER_API_KEY` | **Yes** | All LLM, embedding, reranking via OpenRouter |
| `NEO4J_PASSWORD` | For Neo4j pipelines | Neo4j auth (default: `password`) |
| `COHERE_API_KEY` | For `cohere` reranker only | Direct Cohere Rerank API |
| `OPENAI_API_KEY` | Optional | Direct OpenAI (bypass OpenRouter) |
| `ANTHROPIC_API_KEY` | Optional | Direct Anthropic (bypass OpenRouter) |

---

## Project structure

```
Rag_benchmark/
├── backend/
│   ├── adapters/
│   │   ├── chunkers/           # 8 chunking strategies
│   │   ├── embedders/          # OpenRouter, OpenAI, HuggingFace
│   │   ├── vector_stores/      # Qdrant, Chroma, Neo4j
│   │   ├── pipelines/          # Modular, GraphRAG, Obsidian
│   │   ├── rerankers/          # none, cross_encoder, openrouter, cohere
│   │   └── query_transformers/ # none, hyde
│   ├── api/routes/             # experiments, datasets, registry
│   ├── datasets/sources/       # 8 dataset sources
│   ├── evaluation/             # RAGAS + DeepEval metrics
│   ├── interfaces/             # Protocol definitions
│   ├── models/                 # Pydantic models
│   ├── factory.py              # Auto-import + build functions
│   └── registry.py             # @register decorator
├── frontend/src/
│   ├── pages/                  # Experiments, Run, Dashboard, Datasets, Leaderboard
│   └── components/             # ConfigBuilder, Dashboard, RunMonitor, PipelineVisualizer
├── docs/
│   └── hyde.md                 # HyDE technique documentation
├── CLAUDE.md                   # Developer reference for Claude Code
├── docker-compose.yml
└── .env.example
```
