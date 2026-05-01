"""Football & volleyball datasets via Wikipedia API + HuggingFace SoccerNet."""
from __future__ import annotations
import uuid
from typing import Any
from backend.datasets.sources_registry import source

# Wikipedia queries covering key football / volleyball topics
_FOOTBALL_QUERIES = [
    "FIFA World Cup history",
    "UEFA Champions League",
    "Premier League season",
    "La Liga football Spain",
    "Robert Lewandowski career",
    "Lionel Messi biography",
    "Cristiano Ronaldo career statistics",
    "football tactics formations",
]

_VOLLEYBALL_QUERIES = [
    "FIVB Volleyball World Championship",
    "volleyball rules regulations",
    "Wilfredo Leon volleyball",
    "Polish volleyball national team",
    "volleyball spike technique",
    "beach volleyball Olympics",
]


def _wiki_pages(queries: list[str], max_per_query: int) -> list[dict]:
    from backend.datasets.sources.wikipedia import _search_titles, _fetch_page
    documents = []
    seen: set[str] = set()
    for query in queries:
        for title in _search_titles(query, max_per_query):
            if title in seen:
                continue
            seen.add(title)
            text, url = _fetch_page(title)
            if len(text.split()) < 50:
                continue
            doc_id = str(uuid.uuid5(uuid.NAMESPACE_URL, url))
            documents.append({
                "id": doc_id,
                "text": text[:8000],
                "metadata": {
                    "title": title,
                    "url": url,
                    "source": "wikipedia",
                },
            })
    return documents


@source("football")
def build(config: dict[str, Any]) -> dict:
    """Football (soccer) — Wikipedia articles on clubs, players, tournaments."""
    max_per_query = int(config.get("max_per_query", 3))
    custom_queries = config.get("queries", [])
    queries = custom_queries if custom_queries else _FOOTBALL_QUERIES

    documents = _wiki_pages(queries, max_per_query)
    return {
        "documents": documents,
        "qa_pairs": [],
        "source": "football",
        "domain": "football",
    }


@source("volleyball")
def build_volleyball(config: dict[str, Any]) -> dict:
    """Volleyball — Wikipedia articles on teams, players, tournaments."""
    max_per_query = int(config.get("max_per_query", 3))
    custom_queries = config.get("queries", [])
    queries = custom_queries if custom_queries else _VOLLEYBALL_QUERIES

    documents = _wiki_pages(queries, max_per_query)
    return {
        "documents": documents,
        "qa_pairs": [],
        "source": "volleyball",
        "domain": "volleyball",
    }
