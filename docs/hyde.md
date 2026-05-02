# HyDE — Hypothetical Document Embeddings

**Paper:** Gao et al., 2022 — *Precise Zero-Shot Dense Retrieval without Relevance Labels*

## Idea

Standard dense retrieval embeds the user's **question** and finds the nearest document chunks.
The problem: a short question ("What are PKO BP ATM fees?") lives in a different part of embedding
space than the actual answer passage ("PKO BP charges 0 PLN for ATM withdrawals…").

HyDE bridges this gap:

```
User question
     │
     ▼
  LLM generates a hypothetical answer        ← may be factually wrong
     │
     ▼
  Embed the hypothetical answer              ← now closer to real answer chunks
     │
     ▼
  Vector search with hypothetical embedding
     │
     ▼
  Reranker scores chunks vs ORIGINAL question
     │
     ▼
  LLM generates final answer from real chunks
```

The LLM does **not** need to be correct. A plausible-sounding but hallucinated passage still occupies
embedding space close to real passages on the same topic.

## Configuration

```json
{
  "pipeline": "qdrant_dense",
  "query_transformer": "hyde",
  "hyde_model": "anthropic/claude-haiku-4-5-20251001",
  "hyde_max_tokens": 256,
  "reranker": "openrouter",
  "top_k": 5,
  "retrieve_k": 20
}
```

| Parameter | Default | Description |
|---|---|---|
| `query_transformer` | `none` | Set to `hyde` to enable |
| `hyde_model` | `anthropic/claude-haiku-4-5-20251001` | OpenRouter model for hypothesis generation |
| `hyde_max_tokens` | `256` | Max tokens for the hypothetical passage |
| `hyde_instruction` | built-in | Custom system instruction for the LLM |

## All LLM calls go through OpenRouter

This project uses a **single API key** (`OPENROUTER_API_KEY`) for all LLM interactions:

| Component | What it does | OpenRouter model example |
|---|---|---|
| `hyde` query transformer | Generates hypothetical answer | `anthropic/claude-haiku-4-5-20251001` |
| `openrouter` reranker | Ranks retrieved chunks by relevance | `anthropic/claude-haiku-4-5-20251001` |
| `ModularPipeline` generation | Produces final answer from context | `anthropic/claude-haiku-4-5-20251001` |
| `openrouter/*` embedder | Embeds queries and documents | `openai/text-embedding-3-small` |

OpenRouter provides a unified billing dashboard and lets you switch model providers (Anthropic, OpenAI,
Google, Mistral, etc.) without changing code — only the model name string in the experiment config.

## When HyDE helps vs hurts

| Scenario | Effect |
|---|---|
| Short, ambiguous questions | **+** Better recall |
| Factual, knowledge-dense corpora (TOiP, FinQA) | **+** Significant improvement |
| Questions already phrased like document titles | **±** Neutral |
| Highly specific numerical lookups | **−** Hallucinated numbers may mislead retrieval |
| Low-latency requirements | **−** Adds one LLM call per query |

## Benchmark recommendation

Run two experiments with identical configs except `query_transformer: none` vs `query_transformer: hyde`
and compare on the Leaderboard page. Key metrics to watch: `context_recall` (did we find the right
chunks?) and `faithfulness` (did the answer stick to retrieved context?).

## Implementation

- `backend/adapters/query_transformers/hyde_transformer.py`
- `backend/adapters/query_transformers/none_transformer.py` (passthrough baseline)
- `backend/interfaces/query_transformer.py` (Protocol)

The reranker receives the **original question** (not the HyDE passage) so relevance scoring is
always grounded in what the user actually asked.
