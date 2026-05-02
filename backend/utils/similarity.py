"""Shared utility: cosine similarity between two float vectors."""
from __future__ import annotations


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Return cosine similarity in [0, 1]. Returns 0.0 for zero-norm vectors."""
    dot    = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0
