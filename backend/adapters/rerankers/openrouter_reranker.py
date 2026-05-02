"""
OpenRouter LLM reranker — listwise ranking, single API call.

Sends all candidate passages to the LLM in one request and asks it to
return a ranked ordering. Works with any chat model on OpenRouter.

Advantages over cross-encoder:
  + No local GPU needed
  + One API call for all candidates (vs N calls for pointwise)
  + Can follow nuanced instructions (language, domain)
Disadvantages:
  - LLM latency + cost per query
  - Ranking quality depends on model

Usage in experiment config:
  reranker: openrouter
  reranker_model: anthropic/claude-haiku-4-5-20251001   (default)
  openrouter_api_key: ...                               (or OPENROUTER_API_KEY env)
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

from backend.registry import register
from backend.interfaces.pipeline import Chunk

_OPENROUTER_BASE = "https://openrouter.ai/api/v1"

_SYSTEM = (
    "You are a relevance ranking assistant. "
    "Given a question and a list of passages, rank the passages from most to least relevant. "
    "Output ONLY a valid JSON array of the passage indices (0-based), most relevant first. "
    "Example: [2, 0, 3, 1]"
)


@register("reranker", "openrouter")
class OpenRouterReranker:
    def __init__(self, config: dict[str, Any] | None = None):
        import openai
        cfg = config or {}
        self._model = cfg.get("reranker_model", "anthropic/claude-haiku-4-5-20251001")
        self._client = openai.OpenAI(
            api_key=cfg.get("openrouter_api_key") or os.environ["OPENROUTER_API_KEY"],
            base_url=_OPENROUTER_BASE,
            default_headers={
                "HTTP-Referer": "https://github.com/fifmazurkiewicz/Rag_benchmark",
                "X-Title": "RAG Benchmark",
            },
        )

    def rerank(self, query: str, chunks: list[Chunk], top_k: int) -> list[Chunk]:
        if not chunks:
            return []

        passages = "\n\n".join(
            f"[{i}] {c.text[:600]}" for i, c in enumerate(chunks)
        )
        user_msg = f"Question: {query}\n\nPassages:\n{passages}"

        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=256,
            temperature=0,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": user_msg},
            ],
        )
        raw = response.choices[0].message.content or "[]"
        order = _parse_ranking(raw, len(chunks))

        result = []
        for rank, idx in enumerate(order[:top_k]):
            chunk = chunks[idx]
            chunk.metadata["rerank_score"] = 1.0 - rank / len(order)
            result.append(chunk)
        return result


def _parse_ranking(text: str, n: int) -> list[int]:
    """Extract integer array from LLM output; fallback to identity order."""
    try:
        match = re.search(r"\[[\d,\s]+\]", text)
        if match:
            order = json.loads(match.group())
            valid = [i for i in order if isinstance(i, int) and 0 <= i < n]
            seen = set()
            deduped = [i for i in valid if not (i in seen or seen.add(i))]  # type: ignore[func-returns-value]
            missing = [i for i in range(n) if i not in seen]
            return deduped + missing
    except Exception:
        pass
    return list(range(n))
