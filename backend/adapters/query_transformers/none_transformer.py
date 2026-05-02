"""Passthrough — no transformation, original query goes to retriever."""
from backend.registry import register


@register("query_transformer", "none")
class NoneTransformer:
    def __init__(self, config=None): pass

    def transform(self, query: str) -> str:
        return query
