from __future__ import annotations

import json
import pathlib

from backend.interfaces import Document

DATASETS_DIR = pathlib.Path("datasets_store")


def load_dataset(name: str) -> dict:
    """
    Load a dataset from datasets_store/.

    Checks in order:
      1. datasets_store/<name>.json   — legacy JSON format
      2. datasets_store/<name>/       — Markdown directory (one .md per document)
    """
    json_path = DATASETS_DIR / f"{name}.json"
    md_dir = DATASETS_DIR / name

    if json_path.exists():
        return _load_json(json_path)
    if md_dir.is_dir():
        return _load_md_dir(md_dir)
    raise FileNotFoundError(
        f"Dataset '{name}' not found. "
        f"Checked: {json_path}, {md_dir}/"
    )


def _load_json(path: pathlib.Path) -> dict:
    data = json.loads(path.read_text())
    docs = [
        Document(id=d["id"], text=d["text"], metadata=d.get("metadata", {}))
        for d in data.get("documents", [])
    ]
    return {"documents": docs, "qa_pairs": data.get("qa_pairs", [])}


def _load_md_dir(directory: pathlib.Path) -> dict:
    """
    Load a Markdown dataset directory produced by markdown_store.save_dataset().

    Each .md file has YAML frontmatter with id + metadata, body is the document text.
    """
    from backend.datasets.markdown_store import load_dataset_md
    raw_docs = load_dataset_md(directory.name)
    docs = [
        Document(id=d["id"], text=d["text"], metadata=d.get("metadata", {}))
        for d in raw_docs
    ]
    return {"documents": docs, "qa_pairs": []}
