"""
Obsidian vault loader — "second brain" RAG approach inspired by Karpathy.

Karpathy's insight: your Obsidian vault is not a pile of flat documents —
it's a personal knowledge GRAPH. Every [[wikilink]] is an edge.
Backlinks give you context that isn't written in the note you're reading.

What this does:
  1. Walks the vault and reads every .md file
  2. Parses YAML frontmatter as structured metadata
  3. Extracts [[wikilinks]] and #tags
  4. Builds a bidirectional backlink index
  5. Returns Documents with graph metadata attached
"""
from __future__ import annotations

import pathlib
import re
import uuid
from typing import Any

from backend.interfaces import Document

_FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_WIKILINK    = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")
_TAG         = re.compile(r"(?<!\S)#([A-Za-z0-9_/-]+)")
_HEADING     = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    m = _FRONTMATTER.match(text)
    if not m:
        return {}, text
    try:
        import yaml
        meta = yaml.safe_load(m.group(1)) or {}
    except Exception:
        meta = {}
    return meta, text[m.end():]


def _strip_wikilinks(text: str) -> str:
    """[[Note|alias]] → alias,  [[Note]] → Note"""
    def _repl(m: re.Match) -> str:
        inner = m.group(0)[2:-2]
        return inner.split("|")[-1].split("#")[0].strip()
    return re.sub(r"\[\[([^\]]+)\]\]", _repl, text)


def load_vault(
    vault_path: str,
    excluded_folders: list[str] | None = None,
) -> tuple[list[Document], dict[str, list[str]]]:
    """
    Load all .md notes from an Obsidian vault.

    Returns:
        documents  — one Document per note, with backlink metadata
        link_graph — {note_id: [linked_note_id, ...]} resolved bidirectional graph
    """
    excluded = set(excluded_folders or [".obsidian", ".trash", "templates", "Templates"])
    root = pathlib.Path(vault_path).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"Vault not found: {root}")

    note_files = [
        md for md in root.rglob("*.md")
        if not any(part in excluded for part in md.parts)
    ]

    # title → stable uuid so wikilinks can be resolved across notes
    file_to_id: dict[pathlib.Path, str] = {
        md: str(uuid.uuid5(uuid.NAMESPACE_URL, str(md))) for md in note_files
    }
    title_to_id: dict[str, str] = {md.stem.lower(): file_to_id[md] for md in note_files}

    documents: list[Document] = []
    raw_links: dict[str, list[str]] = {}

    for md in note_files:
        note_id = file_to_id[md]
        raw = md.read_text(encoding="utf-8", errors="replace")
        frontmatter, body = _parse_frontmatter(raw)

        wikilinks = [m.group(1).strip().lower() for m in _WIKILINK.finditer(body)]
        tags      = _TAG.findall(body)
        headings  = [m.group(2).strip() for m in _HEADING.finditer(body)]
        clean     = _strip_wikilinks(body).strip()

        documents.append(Document(
            id=note_id,
            text=clean,
            metadata={
                "title":          md.stem,
                "path":           str(md.relative_to(root)),
                "frontmatter":    frontmatter,
                "tags":           tags,
                "headings":       headings,
                "wikilinks_raw":  wikilinks,
                "word_count":     len(clean.split()),
                "source":         "obsidian_vault",
            },
        ))
        raw_links[note_id] = wikilinks

    # Resolve wikilink titles → ids and build backlink index
    link_graph: dict[str, list[str]] = {d.id: [] for d in documents}
    backlinks:  dict[str, list[str]] = {d.id: [] for d in documents}

    for doc in documents:
        for title in raw_links[doc.id]:
            target = title_to_id.get(title)
            if target and target != doc.id:
                link_graph[doc.id].append(target)
                backlinks[target].append(doc.id)

    id_to_title = {d.id: d.metadata["title"] for d in documents}
    for doc in documents:
        doc.metadata["backlink_ids"]    = backlinks[doc.id]
        doc.metadata["backlink_titles"] = [id_to_title.get(b, "") for b in backlinks[doc.id]]
        doc.metadata["outlink_ids"]     = link_graph[doc.id]

    return documents, link_graph


def vault_to_dataset(vault_path: str, excluded_folders: list[str] | None = None) -> dict:
    """Convert vault to the standard {documents, qa_pairs} dataset format."""
    docs, link_graph = load_vault(vault_path, excluded_folders)
    return {
        "documents":   [{"id": d.id, "text": d.text, "metadata": d.metadata} for d in docs],
        "qa_pairs":    [],
        "link_graph":  link_graph,
        "source":      "obsidian_vault",
        "vault_path":  vault_path,
        "note_count":  len(docs),
    }
