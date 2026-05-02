"""
HyDE — Hypothetical Document Embeddings (Gao et al., 2022).

Instead of embedding the raw question, the LLM first generates a
hypothetical answer (which may be hallucinated). That answer is then
embedded and used for vector search. The intuition: a fake-but-plausible
answer lives much closer in embedding space to real relevant documents
than a short question does.

Effect on retrieval quality:
  + Better recall for factual / knowledge-dense corpora
  + Particularly strong when questions are short and ambiguous
  - Can hurt precision if the hallucinated answer leads retrieval astray
  - Adds one LLM call per query (latency + cost)

All LLM calls go through OpenRouter (OPENROUTER_API_KEY).

Usage in experiment config:
  query_transformer: hyde
  hyde_model: anthropic/claude-haiku-4-5-20251001   (default)
  hyde_max_tokens: 256
  hyde_instruction: "..."                            (optional custom prompt)
"""
from __future__ import annotations

import os
from typing import Any

from backend.registry import register

_OPENROUTER_BASE = "https://openrouter.ai/api/v1"

_DEFAULT_INSTRUCTION = (
    "You are a helpful assistant. Generate a single short passage (2-4 sentences) "
    "that would directly answer the following question. "
    "Write as if it were an excerpt from a relevant document. "
    "Do not explain your reasoning — output only the passage."
)


@register("query_transformer", "hyde")
class HyDETransformer:
    def __init__(self, config: dict[str, Any] | None = None):
        import openai
        cfg = config or {}
        self._model = cfg.get("hyde_model", "anthropic/claude-haiku-4-5-20251001")
        self._max_tokens = int(cfg.get("hyde_max_tokens", 256))
        self._instruction = cfg.get("hyde_instruction", _DEFAULT_INSTRUCTION)
        self._client = openai.OpenAI(
            api_key=cfg.get("openrouter_api_key") or os.environ["OPENROUTER_API_KEY"],
            base_url=_OPENROUTER_BASE,
            default_headers={
                "HTTP-Referer": "https://github.com/fifmazurkiewicz/Rag_benchmark",
                "X-Title": "RAG Benchmark",
            },
        )

    def transform(self, query: str) -> str:
        """Return a hypothetical answer passage to use as the retrieval query."""
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=[
                {
                    "role": "user",
                    "content": f"{self._instruction}\n\nQuestion: {query}",
                }
            ],
        )
        return response.choices[0].message.content.strip()
