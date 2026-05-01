"""Wikipedia API loader — free text corpus for any domain."""
from __future__ import annotations
import uuid
import urllib.parse
import urllib.request
import json
from typing import Any
from backend.datasets.sources_registry import source

_API = "https://en.wikipedia.org/w/api.php"
_HEADERS = {"User-Agent": "RAGBenchmark/1.0 (research; contact@example.com)"}


def _api(params: dict) -> dict:
    url = _API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def _search_titles(query: str, limit: int) -> list[str]:
    data = _api({
        "action": "query", "list": "search",
        "srsearch": query, "srlimit": limit,
        "format": "json",
    })
    return [r["title"] for r in data["query"]["search"]]


def _fetch_page(title: str) -> tuple[str, str]:
    """Returns (plain_text, url)."""
    data = _api({
        "action": "query", "titles": title,
        "prop": "extracts", "explaintext": True,
        "exsectionformat": "plain",
        "format": "json",
    })
    pages = data["query"]["pages"]
    page  = next(iter(pages.values()))
    text  = page.get("extract", "") or ""
    url   = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title)}"
    return text.strip(), url


@source("wikipedia")
def build(config: dict[str, Any]) -> dict:
    """Wikipedia — free text for any domain via search query."""
    query    = config.get("query", "")
    max_docs = int(config.get("max_docs", 20))

    if not query:
        raise ValueError("wikipedia source requires 'query' config key")

    titles    = _search_titles(query, max_docs)
    documents = []

    for title in titles:
        text, url = _fetch_page(title)
        if len(text.split()) < 50:
            continue
        doc_id = str(uuid.uuid5(uuid.NAMESPACE_URL, url))
        documents.append({
            "id": doc_id,
            "text": text[:8000],        # cap at 8k chars per article
            "metadata": {
                "title":  title,
                "url":    url,
                "domain": config.get("domain", "general"),
                "source": "wikipedia",
            },
        })

    return {
        "documents": documents,
        "qa_pairs": [],                 # generated separately via DatasetBuilder
        "source": "wikipedia",
        "query": query,
    }
