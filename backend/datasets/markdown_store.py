"""
Markdown-based dataset storage.

Structure on disk:
    datasets_store/
        <dataset_name>/
            _meta.json          ← dataset metadata (source, domain, stats)
            <doc_id>.md         ← one file per document, YAML frontmatter + body

Why Markdown?
- Human readable and auditable
- Version-control friendly (git diff works)
- Preserves structure (headings, tables) that Docling extracts
- Re-chunkable with different strategies without re-downloading source
- Works perfectly with the ObsidianChunker and MarkdownChunker

Frontmatter example:
    ---
    id: 3f2a1b...
    bank: pko_bp
    label: PKO BP – Taryfa opłat i prowizji
    segment: individual
    source: toip_banks
    domain: financial
    url: https://...
    ---
    # PKO BP Taryfa Opłat i Prowizji
    ...markdown body...
"""
from __future__ import annotations

import json
import pathlib
import re
from typing import Any

from backend.interfaces import Document

DATASETS_DIR = pathlib.Path("datasets_store")


def dataset_path(name: str) -> pathlib.Path:
    return DATASETS_DIR / name


def save_dataset(
    name: str,
    documents: list[dict],
    meta: dict[str, Any] | None = None,
) -> pathlib.Path:
    """
    Persist a list of {id, text, metadata} dicts as Markdown files.
    Returns the dataset directory path.
    """
    root = dataset_path(name)
    root.mkdir(parents=True, exist_ok=True)

    for doc in documents:
        _write_md(root, doc["id"], doc["text"], doc.get("metadata", {}))

    # Write dataset metadata
    meta_path = root / "_meta.json"
    meta_path.write_text(json.dumps({
        "name":       name,
        "doc_count":  len(documents),
        "source":     meta.get("source", "") if meta else "",
        "domain":     meta.get("domain", "") if meta else "",
        **(meta or {}),
    }, indent=2, ensure_ascii=False))

    return root


def load_dataset_md(name: str) -> list[Document]:
    """Load all .md files from a dataset directory as Document objects."""
    root = dataset_path(name)
    if not root.exists():
        raise FileNotFoundError(f"Dataset '{name}' not found at {root}")

    docs: list[Document] = []
    for md_file in sorted(root.glob("*.md")):
        doc_id, text, frontmatter = _read_md(md_file)
        docs.append(Document(id=doc_id, text=text, metadata=frontmatter))
    return docs


def list_datasets_md() -> list[dict]:
    """List all Markdown-based datasets."""
    result = []
    for d in sorted(DATASETS_DIR.iterdir()):
        if not d.is_dir():
            continue
        meta_path = d / "_meta.json"
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        doc_count = len(list(d.glob("*.md")))
        result.append({
            "name":      d.name,
            "doc_count": doc_count,
            "qa_count":  0,          # Markdown datasets have no QA pairs
            "source":    meta.get("source", "markdown"),
            "format":    "markdown",
        })
    return result


# ── internal helpers ────────────────────────────────────────────────────────

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _write_md(root: pathlib.Path, doc_id: str, text: str, metadata: dict) -> None:
    import yaml
    frontmatter = yaml.dump({"id": doc_id, **metadata},
                             allow_unicode=True, default_flow_style=False).strip()
    content = f"---\n{frontmatter}\n---\n\n{text}"
    safe_id = re.sub(r"[^\w\-]", "_", doc_id)[:80]
    (root / f"{safe_id}.md").write_text(content, encoding="utf-8")


def _read_md(path: pathlib.Path) -> tuple[str, str, dict]:
    """Returns (doc_id, body_text, frontmatter_dict)."""
    raw = path.read_text(encoding="utf-8", errors="replace")
    m = _FRONTMATTER_RE.match(raw)
    if m:
        import yaml
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except Exception:
            fm = {}
        body = raw[m.end():].strip()
        doc_id = str(fm.get("id", path.stem))
        return doc_id, body, fm
    return path.stem, raw.strip(), {}
