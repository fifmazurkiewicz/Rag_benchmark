"""
TOiP (Taryfa Opłat i Prowizji) scraper — major Polish banks.

Downloads publicly available PDF fee schedules and returns them as plain
documents ready for RAG. No QA generation — just clean text for retrieval.

Banks covered:
  PKO BP, Pekao, ING, mBank, Santander, Millennium, BNP Paribas, Alior,
  Credit Agricole, Citi Handlowy

Each bank may publish multiple TOiPs (individual / business / premium).
All are fetched unless segment filter is applied.
"""
from __future__ import annotations

import io
import time
import uuid
import urllib.request
import urllib.error
from typing import Any

from backend.datasets.sources_registry import source

_UA = "Mozilla/5.0 (RAGBenchmark/1.0; research; +https://github.com/fifmazurkiewicz/Rag_benchmark)"

# ---------------------------------------------------------------------------
# Known TOiP document URLs per bank
# Format: {bank_id: [{label, url, segment}]}
# URLs point to publicly available PDFs (no login required).
# ---------------------------------------------------------------------------
_BANK_DOCS: dict[str, list[dict[str, str]]] = {
    "pko_bp": [
        {
            "label": "PKO BP – Taryfa opłat i prowizji – klienci indywidualni",
            "url": "https://www.pkobp.pl/api/public/e760bc4b-b590-4cba-8668-7f4bbebc4e31.pdf",
            "segment": "individual",
        },
        {
            "label": "PKO BP – Taryfa opłat i prowizji – MŚP",
            "url": "https://www.pkobp.pl/api/public/d1e0b72b-4c1a-4b53-9c2e-3f5a6e8d9c11.pdf",
            "segment": "business",
        },
    ],
    "pekao": [
        {
            "label": "Bank Pekao – Taryfa prowizji i opłat – oferta bieżąca",
            "url": "https://www.pekao.com.pl/dam/jcr:eab0d421-5e06-4d39-a23a-a4b9a98e9c0c/Taryfa-prowizji-i-oplat-oferta-biezaca-od-1-11-2025.pdf",
            "segment": "individual",
        },
    ],
    "ing": [
        {
            "label": "ING Bank Śląski – Tabela opłat i prowizji – klienci indywidualni",
            "url": "https://www.ing.pl/_fileserver/item/1522877",
            "segment": "individual",
        },
        {
            "label": "ING Bank Śląski – Tabela opłat i prowizji – przedsiębiorcy",
            "url": "https://www.ing.pl/_fileserver/item/1522878",
            "segment": "business",
        },
    ],
    "mbank": [
        {
            "label": "mBank – Taryfa prowizji i opłat – eKonto osobiste",
            "url": "https://pdf.mbank.pl/mbankpl/of/tpio/taryfa-prowizji-i-oplat-ekonto.pdf",
            "segment": "individual",
        },
        {
            "label": "mBank – Taryfa prowizji i opłat – mBiznes Konto",
            "url": "https://pdf.mbank.pl/mbankpl/of/tpio/taryfa-prowizji-i-oplat-mbiznes.pdf",
            "segment": "business",
        },
    ],
    "santander": [
        {
            "label": "Santander Bank Polska – Taryfa opłat i prowizji – klienci indywidualni",
            "url": "https://www.santander.pl/content/dam/santander-consumer-bank/poland/taryfa/taryfa-oplat-i-prowizji-klienci-indywidualni.pdf",
            "segment": "individual",
        },
        {
            "label": "Santander Bank Polska – Taryfa opłat i prowizji – MŚP",
            "url": "https://www.santander.pl/content/dam/santander-consumer-bank/poland/taryfa/taryfa-oplat-i-prowizji-msp.pdf",
            "segment": "business",
        },
    ],
    "millennium": [
        {
            "label": "Bank Millennium – Taryfa opłat i prowizji – klienci indywidualni",
            "url": "https://www.bankmillennium.pl/documents/10184/0/Taryfa_Oplat_Prowizji_Klienci_Indywidualni.pdf",
            "segment": "individual",
        },
        {
            "label": "Bank Millennium – Taryfa opłat i prowizji – przedsiębiorcy",
            "url": "https://www.bankmillennium.pl/documents/10184/0/Taryfa_Oplat_Prowizji_Przedsiebiorcy.pdf",
            "segment": "business",
        },
    ],
    "bnp_paribas": [
        {
            "label": "BNP Paribas – Taryfa opłat i prowizji – klienci indywidualni",
            "url": "https://www.bnpparibas.pl/content/dam/bnpparibas-pl/dokumenty/taryfa/taryfa-oplat-klienci-indywidualni.pdf",
            "segment": "individual",
        },
        {
            "label": "BNP Paribas – Taryfa opłat i prowizji – MŚP",
            "url": "https://www.bnpparibas.pl/content/dam/bnpparibas-pl/dokumenty/taryfa/taryfa-oplat-msp.pdf",
            "segment": "business",
        },
    ],
    "alior": [
        {
            "label": "Alior Bank – Taryfa opłat i prowizji – klienci indywidualni",
            "url": "https://www.aliorbank.pl/content/dam/alior/dokumenty/taryfa/TOiP_klienci_indywidualni.pdf",
            "segment": "individual",
        },
    ],
    "credit_agricole": [
        {
            "label": "Credit Agricole – Taryfa opłat i prowizji – klienci indywidualni",
            "url": "https://www.credit-agricole.pl/content/dam/taryfy/taryfa-oplat-i-prowizji-klienci-indywidualni.pdf",
            "segment": "individual",
        },
    ],
    "citi_handlowy": [
        {
            "label": "Citi Handlowy – Taryfa opłat i prowizji",
            "url": "https://www.citibank.pl/poland/consumer/language2/poland/pdf/taryfa-oplat-i-prowizji.pdf",
            "segment": "individual",
        },
    ],
}


def _download(url: str, timeout: int = 30) -> bytes | None:
    """Download URL → bytes. Returns None on any error."""
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except (urllib.error.URLError, urllib.error.HTTPError, Exception):
        return None


def _pdf_to_markdown(data: bytes, url: str = "") -> str:
    """Convert PDF bytes to Markdown via Docling (falls back to pdfplumber)."""
    from backend.datasets.docling_converter import convert_pdf_to_markdown
    return convert_pdf_to_markdown(data, origin_url=url)


@source("toip_banks")
def build(config: dict[str, Any]) -> dict:
    """
    TOiP Polish banks — publicly available fee schedules as plain documents.
    No QA pairs — pure document corpus for RAG retrieval.

    Config options:
        banks    — list of bank ids to include, e.g. ["pko_bp", "pekao"]
                   default: all banks
        segment  — "individual" | "business" | "all" (default: "all")
        delay    — seconds between requests (default: 1.5)
    """
    selected_banks: list[str] = config.get("banks", list(_BANK_DOCS.keys()))
    segment_filter: str       = config.get("segment", "all")
    delay: float              = float(config.get("delay", 1.5))

    documents: list[dict] = []
    errors:    list[dict] = []

    for bank_id in selected_banks:
        entries = _BANK_DOCS.get(bank_id, [])
        for entry in entries:
            if segment_filter != "all" and entry["segment"] != segment_filter:
                continue

            url   = entry["url"]
            label = entry["label"]

            pdf_bytes = _download(url)
            time.sleep(delay)

            if pdf_bytes is None:
                errors.append({"bank": bank_id, "url": url, "error": "download_failed"})
                continue

            try:
                text = _pdf_to_markdown(pdf_bytes, url=url)
            except Exception as exc:
                errors.append({"bank": bank_id, "url": url, "error": str(exc)})
                continue

            if len(text.split()) < 20:
                errors.append({"bank": bank_id, "url": url, "error": "empty_or_scanned_pdf"})
                continue

            doc_id = str(uuid.uuid5(uuid.NAMESPACE_URL, url))
            documents.append({
                "id": doc_id,
                "text": text,          # Markdown — tables, headings preserved
                "metadata": {
                    "bank":    bank_id,
                    "label":   label,
                    "segment": entry["segment"],
                    "url":     url,
                    "domain":  "financial",
                    "source":  "toip_banks",
                    "format":  "markdown",
                },
            })

    return {
        "documents": documents,
        "qa_pairs":  [],        # intentionally empty — use RAG to query
        "source":    "toip_banks",
        "domain":    "financial",
        "errors":    errors,    # report which PDFs failed
        "stats": {
            "requested": sum(
                len([e for e in _BANK_DOCS.get(b, [])
                     if segment_filter == "all" or e["segment"] == segment_filter])
                for b in selected_banks
            ),
            "fetched": len(documents),
            "failed":  len(errors),
        },
    }
