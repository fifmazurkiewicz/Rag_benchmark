from __future__ import annotations
import json
import pathlib
from backend.interfaces import Document

DATASETS_DIR = pathlib.Path("datasets_store")


def load_dataset(name: str) -> dict:
    """Load a dataset JSON from datasets_store/. Returns {documents, qa_pairs}."""
    path = DATASETS_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Dataset '{name}' not found at {path}")
    data = json.loads(path.read_text())
    docs = [
        Document(id=d["id"], text=d["text"], metadata=d.get("metadata", {}))
        for d in data.get("documents", [])
    ]
    return {"documents": docs, "qa_pairs": data.get("qa_pairs", [])}
