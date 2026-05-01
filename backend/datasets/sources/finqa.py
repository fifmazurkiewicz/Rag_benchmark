"""FinQA — financial numerical reasoning over SEC earnings reports. ~8K QA pairs."""
from __future__ import annotations
import json, uuid
from typing import Any
from backend.datasets.sources_registry import source


@source("finqa")
def build(config: dict[str, Any]) -> dict:
    """FinQA — financial numerical reasoning over SEC earnings reports. ~8K QA pairs."""
    from datasets import load_dataset

    split = config.get("split", "train")
    max_docs = int(config.get("max_docs", 200))

    ds = load_dataset("ibm/finqa", split=split, trust_remote_code=True)

    documents, qa_pairs = [], []
    seen_ids: set[str] = set()

    for row in ds:
        # Each row: pre_text + table + post_text = full context
        pre  = " ".join(row.get("pre_text") or [])
        post = " ".join(row.get("post_text") or [])
        table_rows = row.get("table") or []
        table_text = " | ".join(
            " ".join(str(c) for c in r) for r in table_rows
        )
        text = "\n".join(filter(None, [pre, table_text, post])).strip()
        if not text:
            continue

        doc_id = str(uuid.uuid5(uuid.NAMESPACE_URL, text[:200]))
        if doc_id not in seen_ids:
            seen_ids.add(doc_id)
            documents.append({
                "id": doc_id,
                "text": text,
                "metadata": {
                    "domain": "financial",
                    "source": "finqa",
                    "filename": row.get("filename", ""),
                },
            })

        qa_pairs.append({
            "question": row["question"],
            "answer": str(row.get("answer") or row.get("gold_inds") or ""),
            "doc_id": doc_id,
        })

        if len(documents) >= max_docs:
            break

    return {
        "documents": documents,
        "qa_pairs": qa_pairs,
        "source": "finqa",
        "domain": "financial",
    }
