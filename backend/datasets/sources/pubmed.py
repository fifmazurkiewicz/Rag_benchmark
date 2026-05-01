"""PubMed/NCBI — free medical & neurology abstracts via E-utilities API."""
from __future__ import annotations
import uuid
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import json
import time
from typing import Any
from backend.datasets.sources_registry import source

_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
_EFETCH  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
_HEADERS = {"User-Agent": "RAGBenchmark/1.0 (research)"}


def _get(url: str, params: dict) -> bytes:
    full = url + "?" + urllib.parse.urlencode(params)
    req  = urllib.request.Request(full, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read()


def _search_pmids(query: str, max_results: int, api_key: str = "") -> list[str]:
    params: dict = {
        "db": "pubmed", "term": query,
        "retmax": max_results, "retmode": "json",
    }
    if api_key:
        params["api_key"] = api_key
    data = json.loads(_get(_ESEARCH, params))
    return data["esearchresult"]["idlist"]


def _fetch_abstracts(pmids: list[str], api_key: str = "") -> list[dict]:
    if not pmids:
        return []
    params: dict = {
        "db": "pubmed", "id": ",".join(pmids),
        "rettype": "abstract", "retmode": "xml",
    }
    if api_key:
        params["api_key"] = api_key
    xml_bytes = _get(_EFETCH, params)
    root      = ET.fromstring(xml_bytes)
    results   = []

    for article in root.findall(".//PubmedArticle"):
        pmid_el    = article.find(".//PMID")
        title_el   = article.find(".//ArticleTitle")
        abstract_el = article.find(".//AbstractText")

        pmid     = pmid_el.text if pmid_el is not None else ""
        title    = title_el.text if title_el is not None else ""
        abstract = abstract_el.text if abstract_el is not None else ""

        if abstract:
            results.append({"pmid": pmid, "title": title, "abstract": abstract})

    return results


@source("pubmed")
def build(config: dict[str, Any]) -> dict:
    """PubMed — medical/neurology paper abstracts via NCBI E-utilities (free, no key needed)."""
    query    = config.get("query", "neurology")
    max_docs = int(config.get("max_docs", 50))
    api_key  = config.get("ncbi_api_key", "")

    pmids   = _search_pmids(query, max_docs, api_key)
    # NCBI rate limit: 3 req/s without key, 10/s with key
    time.sleep(0.4 if not api_key else 0.15)
    records = _fetch_abstracts(pmids, api_key)

    documents = []
    for rec in records:
        text = f"{rec['title']}\n\n{rec['abstract']}"
        doc_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"pubmed:{rec['pmid']}"))
        documents.append({
            "id": doc_id,
            "text": text,
            "metadata": {
                "domain":  "medical",
                "source":  "pubmed",
                "pmid":    rec["pmid"],
                "title":   rec["title"],
                "url":     f"https://pubmed.ncbi.nlm.nih.gov/{rec['pmid']}/",
            },
        })

    return {
        "documents": documents,
        "qa_pairs": [],
        "source": "pubmed",
        "query": query,
    }
