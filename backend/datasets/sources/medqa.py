"""MedQA — US medical licensing exam questions (USMLE). ~12K QA pairs."""
from __future__ import annotations
import uuid
from typing import Any
from backend.datasets.sources_registry import source


@source("medqa")
def build(config: dict[str, Any]) -> dict:
    """MedQA — US medical licensing exam (USMLE) questions. ~12K QA pairs."""
    from datasets import load_dataset

    split     = config.get("split", "train")
    max_docs  = int(config.get("max_docs", 200))
    subtopic  = config.get("subtopic", "")   # e.g. "neurology" filter

    ds = load_dataset("bigbio/med_qa", name="med_qa_en_bigbio_qa",
                      split=split, trust_remote_code=True)

    documents, qa_pairs = [], []

    for row in ds:
        question = row.get("question", "")
        choices  = row.get("choices", {})
        answer   = row.get("answer", "")

        # Build a document from question + all answer choices (context for RAG)
        options_text = ""
        if isinstance(choices, dict):
            options_text = "\n".join(
                f"{k}: {v}" for k, v in choices.items()
            )
        elif isinstance(choices, list):
            options_text = "\n".join(str(c) for c in choices)

        text = f"{question}\n\nOptions:\n{options_text}"

        if subtopic and subtopic.lower() not in text.lower():
            continue

        doc_id = str(uuid.uuid5(uuid.NAMESPACE_URL, question))
        documents.append({
            "id": doc_id,
            "text": text,
            "metadata": {
                "domain": "medical",
                "source": "medqa",
                "subtopic": subtopic or "general",
            },
        })
        qa_pairs.append({
            "question": question,
            "answer": answer,
            "doc_id": doc_id,
        })

        if len(documents) >= max_docs:
            break

    return {
        "documents": documents,
        "qa_pairs": qa_pairs,
        "source": "medqa",
        "domain": "medical",
    }


@source("medmcqa")
def build_medmcqa(config: dict[str, Any]) -> dict:
    """MedMCQA — 194K medical multiple-choice questions across 21 subjects."""
    from datasets import load_dataset

    split    = config.get("split", "train")
    max_docs = int(config.get("max_docs", 200))
    subject  = config.get("subject", "")  # e.g. "Neurology"

    ds = load_dataset("openlifescienceai/medmcqa", split=split, trust_remote_code=True)

    documents, qa_pairs = [], []

    for row in ds:
        if subject and subject.lower() not in (row.get("subject_name") or "").lower():
            continue

        question = row.get("question", "")
        options  = [row.get(k, "") for k in ("opa", "opb", "opc", "opd")]
        cop      = row.get("cop", 0)                      # correct option index (1-based)
        answer   = options[cop - 1] if 0 < cop <= 4 else ""
        exp      = row.get("exp") or ""

        text = (
            f"{question}\n\n"
            f"A: {options[0]}\nB: {options[1]}\n"
            f"C: {options[2]}\nD: {options[3]}\n"
            + (f"\nExplanation: {exp}" if exp else "")
        )
        doc_id = str(uuid.uuid5(uuid.NAMESPACE_URL, question))
        documents.append({
            "id": doc_id,
            "text": text,
            "metadata": {
                "domain": "medical",
                "source": "medmcqa",
                "subject": row.get("subject_name", ""),
            },
        })
        qa_pairs.append({
            "question": question,
            "answer": answer,
            "doc_id": doc_id,
        })

        if len(documents) >= max_docs:
            break

    return {
        "documents": documents,
        "qa_pairs": qa_pairs,
        "source": "medmcqa",
        "domain": "medical",
    }
