# RAG Benchmark — CLAUDE.md

## Project overview

This is a **RAG (Retrieval-Augmented Generation) benchmarking platform** for comparing
vector databases, chunking strategies, embedders, rerankers, and query techniques against
each other. Every component is swappable via a `@register` decorator — adding a new
chunker, reranker, or pipeline requires creating one file with zero changes elsewhere.

**Stack**: FastAPI backend · React/TypeScript frontend · OpenRouter for all LLM/embedding calls.

---

## Key architectural pattern: the registry

```python
# backend/registry.py
_registry: dict[str, dict[str, type]] = {}

def register(component_type: str, name: str):
    def decorator(cls):
        _registry.setdefault(component_type, {})[name] = cls
        return cls
    return decorator
```

`factory.py` calls `pkgutil.walk_packages("backend/adapters/")` on startup — every module
in `adapters/` is imported, firing all `@register` decorators automatically.
The frontend calls `GET /registry/` and auto-populates dropdowns.

**Component types**: `chunker`, `embedder`, `vector_store`, `pipeline`, `reranker`, `query_transformer`

---

## How to add a new component (the most common task)

### New chunker
Create `backend/adapters/chunkers/<name>.py`:
```python
import uuid
from typing import Any
from backend.registry import register
from backend.interfaces import Document, Chunk

@register("chunker", "my_chunker")
class MyChunker:
    def __init__(self, config: dict[str, Any]):
        self.param = config.get("my_param", default_value)

    def chunk(self, doc: Document) -> list[Chunk]:
        return [
            Chunk(id=str(uuid.uuid4()), doc_id=doc.id, text=piece, index=i,
                  metadata={"chunker": "my_chunker"})
            for i, piece in enumerate(split_logic(doc.text))
        ]
```
Restart backend → `my_chunker` appears in frontend dropdown automatically.

### New reranker
Create `backend/adapters/rerankers/<name>.py`:
```python
from backend.registry import register
from backend.interfaces.pipeline import Chunk

@register("reranker", "my_reranker")
class MyReranker:
    def __init__(self, config=None): ...
    def rerank(self, query: str, chunks: list[Chunk], top_k: int) -> list[Chunk]: ...
```

### New embedder
```python
@register("embedder", "provider/model-name")
class MyEmbedder:
    def __init__(self, config: dict[str, Any]): ...
    def embed(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...
    def dimension(self) -> int: ...
```

### New query transformer
```python
@register("query_transformer", "my_transform")
class MyTransformer:
    def __init__(self, config=None): ...
    def transform(self, query: str) -> str: ...
```

### New dataset source
Create `backend/datasets/sources/<name>.py`:
```python
from backend.datasets.sources_registry import source

@source("my_source")
def build(config: dict) -> dict:
    return {
        "documents": [{"id": ..., "text": ..., "metadata": {...}}],
        "qa_pairs": [],   # or list of {"question": ..., "answer": ...}
        "source": "my_source",
    }
```

---

## Data flow

### Ingest
```
Document list
  → chunker.chunk(doc)                         → list[Chunk]
  → if all chunks have _precomputed_embedding  → use those vectors directly
    else embedder.embed([c.text])              → list[list[float]]
  → vector_store.upsert(chunks, vectors)
```

The `_precomputed_embedding` shortcut is used by `late_chunking` — it encodes the full
document context into each chunk's vector at chunk time, so re-embedding would destroy
that context. Any other chunker leaves the field absent, triggering normal embedding.

### Query
```
user question
  → query_transformer.transform(q)   # HyDE or passthrough
  → embedder.embed_query(transformed)
  → vector_store.search(vec, retrieve_k)   # retrieve_k: 0 → auto (top_k × 4)
  → reranker.rerank(ORIGINAL_question, candidates, top_k)
  → LLM generate(question, top_chunks)  # via OpenRouter
  → PipelineResult
```

**Important**: reranker always scores against the **original** question, not the HyDE-transformed one.

### Pipeline elasticity

Not every pipeline needs every component. `ModularPipeline` wires the full stack
(chunker → embedder → vector_store → query_transformer → reranker → LLM).
Graph pipelines (`neo4j_graphrag`, `falkordb_graphrag`, `obsidian_rag`) are intentionally
simpler — they don't accept a `reranker` or `query_transformer` config key, and that's fine.
Only add those hooks to a pipeline when the architecture actually supports them.

---

## LLM and API keys

**All LLM/embedding calls go through OpenRouter** — single key `OPENROUTER_API_KEY`.

Model name convention: `"provider/model-id"` e.g. `"anthropic/claude-haiku-4-5-20251001"`.

- `ModularPipeline._generate()` → openai client → OpenRouter
- `HyDETransformer.transform()` → openai client → OpenRouter
- `OpenRouterReranker.rerank()` → openai client → OpenRouter
- `OpenRouterEmbedder.embed()` → openai client → OpenRouter

Direct Anthropic/OpenAI/Cohere adapters still exist but are secondary. Don't add new
direct-provider adapters — route through OpenRouter instead.

---

## Files to know

| File | Role |
|---|---|
| `backend/registry.py` | Registry dict + `register()` + `build()` |
| `backend/factory.py` | Auto-import adapters, `build_pipeline()`, `build_chunker()`, `build_embedder()` |
| `backend/interfaces/pipeline.py` | `Document`, `Chunk`, `IngestStats`, `PipelineResult`, `PipelineAdapter` |
| `backend/adapters/pipelines/modular.py` | Main composable pipeline — most experiments use this |
| `backend/api/routes/experiments.py` | Run execution, result caching, Excel export |
| `backend/datasets/loaders.py` | `load_dataset()` — checks JSON then Markdown directory |
| `backend/datasets/markdown_store.py` | Save/load `.md` datasets with YAML frontmatter |
| `backend/datasets/docling_converter.py` | PDF → Markdown (Docling primary, pdfplumber fallback) |
| `frontend/src/api/types.ts` | All TypeScript interfaces — keep in sync with Pydantic models |
| `frontend/src/components/PipelineVisualizer.tsx` | Diagram + JSON view of pipeline config; used in ExperimentsPage and RunPage |

---

## Result caching

Experiments are cached by SHA-256 hash of `(dataset + sorted pipeline configs + metrics)`.
Hash → run_id stored in `results/cache.json`. `POST /experiments/{name}/run?force=true` bypasses.

When adding fields to `PipelineConfig` (Pydantic model), they automatically become part of
the cache key — no extra work needed.

---

## Dataset storage formats

**JSON** (`datasets_store/<name>.json`):
```json
{"documents": [{"id": "...", "text": "...", "metadata": {}}], "qa_pairs": [{"question": "...", "answer": "..."}]}
```

**Markdown directory** (`datasets_store/<name>/<doc_id>.md`):
```markdown
---
id: abc123
bank: pko_bp
source: toip_banks
---
# Document text here...
```
`load_dataset(name)` auto-detects format.

---

## Running locally (without Docker)

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn backend.api.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

Required: Qdrant running on `localhost:6333` (or change `qdrant_host` in config).

---

## Common gotchas

- **New adapter not appearing in frontend**: check `__init__.py` exists in the adapter
  subdirectory and the module is in `backend/adapters/`. `_auto_import_adapters()` uses
  `pkgutil.walk_packages` — it finds everything recursively.

- **`elasticsearch_dense` pipeline still registered**: `ModularPipeline` still registers
  that name (legacy). The Elasticsearch vector store adapter was removed; using this
  pipeline name will fail at query time. Can be cleaned up.

- **FalkorDB GraphRAG**: monolithic SDK — chunker/embedder settings are ignored.
  The frontend warns about this in `PipelineRow`.

- **Reranker sees original question**: even when HyDE is active, `reranker.rerank()` always
  receives `question` (original), not `retrieval_query`. This is intentional.

- **`retrieve_k = 0`** in config means "use `top_k * 4`". The actual value is computed in
  `ModularPipeline.__init__` as `raw = int(cfg.get("retrieve_k", 0)); self._retrieve_k = raw if raw > 0 else top_k * 4`.
  Using `cfg.get("retrieve_k", fallback)` alone was a bug — when the key existed with value 0,
  Python returned 0 (no fallback), causing `search(vec, 0)` → no results. Always use the `or` pattern.

- **Excel export** requires `openpyxl`. If missing, `GET /results/{id}/export` will raise
  `ImportError` at request time (not at startup).
