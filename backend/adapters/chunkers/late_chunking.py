"""
Late Chunking — context-aware chunking via long-context embeddings.

Standard chunking loses cross-chunk context: each chunk is embedded
independently, so "it" in chunk 5 doesn't know what "it" referred to in chunk 2.

Late chunking fixes this:
  1. Encode the ENTIRE document at once with a long-context encoder
     → every token's embedding already contains full document context
  2. THEN split the resulting token embeddings into chunks by position
  3. Each chunk vector = mean-pool of the token embeddings in that span

The result: chunk embeddings that understand their document-level context.

Requirements:
  - A transformer model with sufficient context length (default: BAAI/bge-m3, 8192 tokens)
  - The model must be loaded via sentence-transformers or transformers directly

References:
  - "Late Chunking: Contextual Chunk Embeddings Using Long-Context Embedding Models"
    — JinaAI, 2024 (https://arxiv.org/abs/2409.04701)

Usage in experiment config:
  chunker: late_chunking
  chunk_size: 512          (words per chunk, default 512)
  late_chunking_model: BAAI/bge-m3   (default)
"""
from __future__ import annotations

import uuid
from typing import Any

from backend.registry import register
from backend.interfaces import Document, Chunk


@register("chunker", "late_chunking")
class LateChunkingChunker:
    def __init__(self, config: dict[str, Any]):
        self._chunk_size = int(config.get("chunk_size", 512))
        self._model_name = config.get("late_chunking_model", "BAAI/bge-m3")
        self._tokenizer = None
        self._model = None

    def _load_model(self):
        if self._model is not None:
            return
        from transformers import AutoTokenizer, AutoModel
        self._tokenizer = AutoTokenizer.from_pretrained(self._model_name)
        self._model = AutoModel.from_pretrained(self._model_name)
        self._model.eval()

    def chunk(self, doc: Document) -> list[Chunk]:
        import torch

        self._load_model()

        words = doc.text.split()
        if not words:
            return []

        # ── Step 1: tokenize the full document ───────────────────────────
        encoding = self._tokenizer(
            doc.text,
            return_tensors="pt",
            truncation=True,
            max_length=8192,
            return_offsets_mapping=True,
        )
        offset_mapping = encoding.pop("offset_mapping")[0]  # (seq_len, 2) — char spans

        # ── Step 2: encode the full document — all token embeddings share context ──
        with torch.no_grad():
            output = self._model(**encoding)
        token_embeddings = output.last_hidden_state[0]  # (seq_len, hidden)

        # ── Step 3: split text into word-count chunks, find token spans ──────────
        chunks_text = _split_words(doc.text, self._chunk_size)

        results: list[Chunk] = []
        char_cursor = 0

        for i, chunk_text in enumerate(chunks_text):
            chunk_start_char = doc.text.find(chunk_text, char_cursor)
            if chunk_start_char == -1:
                chunk_start_char = char_cursor
            chunk_end_char = chunk_start_char + len(chunk_text)
            char_cursor = chunk_end_char

            # find token indices that overlap with this char span
            token_mask = (
                (offset_mapping[:, 0] < chunk_end_char) &
                (offset_mapping[:, 1] > chunk_start_char)
            )
            span_embeddings = token_embeddings[token_mask]

            if span_embeddings.shape[0] == 0:
                # fallback: use CLS token
                span_embeddings = token_embeddings[:1]

            # mean-pool → single chunk vector
            chunk_vec = span_embeddings.mean(dim=0).tolist()

            results.append(Chunk(
                id=str(uuid.uuid4()),
                doc_id=doc.id,
                text=chunk_text,
                index=i,
                metadata={
                    "chunker": "late_chunking",
                    "model": self._model_name,
                    # store precomputed embedding so the pipeline can skip re-embedding
                    "_precomputed_embedding": chunk_vec,
                },
            ))

        return results


def _split_words(text: str, chunk_size: int) -> list[str]:
    words = text.split()
    chunks = []
    for start in range(0, len(words), chunk_size):
        piece = " ".join(words[start : start + chunk_size])
        if piece.strip():
            chunks.append(piece)
    return chunks
