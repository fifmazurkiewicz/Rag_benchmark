from __future__ import annotations
import json
import pathlib
from fastapi import APIRouter, UploadFile, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Any

router = APIRouter(prefix="/datasets", tags=["datasets"])

DATASETS_DIR = pathlib.Path("datasets_store")
DATASETS_DIR.mkdir(exist_ok=True)


class DatasetMeta(BaseModel):
    name: str
    doc_count: int
    qa_count: int
    source: str = "upload"


class VaultImportRequest(BaseModel):
    vault_path: str
    dataset_name: str
    excluded_folders: list[str] = []
    generate_qa: bool = False
    qa_per_note: int = 3
    llm_model: str = "claude-haiku-4-5-20251001"


@router.get("/", response_model=list[DatasetMeta])
def list_datasets():
    result = []
    for p in DATASETS_DIR.glob("*.json"):
        try:
            data = json.loads(p.read_text())
            result.append(DatasetMeta(
                name=p.stem,
                doc_count=len(data.get("documents", [])),
                qa_count=len(data.get("qa_pairs", [])),
            ))
        except Exception:
            pass
    return result


@router.get("/{name}")
def get_dataset(name: str):
    path = DATASETS_DIR / f"{name}.json"
    if not path.exists():
        raise HTTPException(404, f"Dataset '{name}' not found")
    return json.loads(path.read_text())


@router.post("/upload")
async def upload_dataset(file: UploadFile):
    content = await file.read()
    name = pathlib.Path(file.filename).stem
    path = DATASETS_DIR / f"{name}.json"
    path.write_bytes(content)
    return {"name": name, "size": len(content)}


@router.delete("/{name}")
def delete_dataset(name: str):
    path = DATASETS_DIR / f"{name}.json"
    if not path.exists():
        raise HTTPException(404, f"Dataset '{name}' not found")
    path.unlink()
    return {"deleted": name}


@router.post("/from-vault")
def import_from_vault(req: VaultImportRequest, background_tasks: BackgroundTasks):
    """
    Import an Obsidian vault as a dataset.
    Optionally generates QA pairs for each note via Claude.
    """
    background_tasks.add_task(_do_vault_import, req)
    return {"status": "importing", "dataset_name": req.dataset_name}


def _do_vault_import(req: VaultImportRequest):
    from backend.datasets.obsidian_loader import vault_to_dataset
    from backend.datasets.generator import generate_qa_pairs

    dataset = vault_to_dataset(req.vault_path, req.excluded_folders or None)

    if req.generate_qa:
        qa: list[dict] = []
        for doc in dataset["documents"]:
            text = doc["text"]
            if len(text.split()) < 30:
                continue
            pairs = generate_qa_pairs(text, n=req.qa_per_note, model=req.llm_model)
            for p in pairs:
                p["doc_id"] = doc["id"]
            qa.extend(pairs)
        dataset["qa_pairs"] = qa

    path = DATASETS_DIR / f"{req.dataset_name}.json"
    path.write_text(json.dumps(dataset, indent=2, ensure_ascii=False))


class SourceBuildRequest(BaseModel):
    source: str
    dataset_name: str
    config: dict[str, Any] = {}
    generate_qa: bool = False
    qa_per_doc: int = 3
    llm_model: str = "claude-haiku-4-5-20251001"


@router.get("/sources/")
def list_sources():
    """List all registered dataset sources."""
    from backend.datasets.sources_registry import available
    return available()


@router.post("/from-source")
def build_from_source(req: SourceBuildRequest, background_tasks: BackgroundTasks):
    """
    Build a dataset from a registered source (finqa, medqa, wikipedia, pubmed, football, volleyball).
    Sources with built-in QA (finqa, medqa, medmcqa) need no generate_qa.
    Sources without QA (wikipedia, pubmed, football, volleyball) can auto-generate via Claude.
    """
    from backend.datasets.sources_registry import available
    names = [s["name"] for s in available()]
    if req.source not in names:
        raise HTTPException(400, f"Unknown source '{req.source}'. Available: {names}")
    background_tasks.add_task(_do_source_build, req)
    return {"status": "building", "dataset_name": req.dataset_name, "source": req.source}


def _do_source_build(req: SourceBuildRequest):
    from backend.datasets.sources_registry import build
    from backend.datasets.generator import generate_qa_pairs

    dataset = build(req.source, req.config)

    if req.generate_qa and not dataset.get("qa_pairs"):
        qa: list[dict] = []
        for doc in dataset["documents"]:
            text = doc["text"]
            if len(text.split()) < 50:
                continue
            pairs = generate_qa_pairs(text, n=req.qa_per_doc, model=req.llm_model)
            for p in pairs:
                p["doc_id"] = doc["id"]
            qa.extend(pairs)
        dataset["qa_pairs"] = qa

    path = DATASETS_DIR / f"{req.dataset_name}.json"
    path.write_text(json.dumps(dataset, indent=2, ensure_ascii=False))


@router.get("/vault/stats")
def vault_stats(vault_path: str):
    """Quick stats about an Obsidian vault before importing."""
    from backend.datasets.obsidian_loader import load_vault
    try:
        docs, link_graph = load_vault(vault_path)
        total_links = sum(len(v) for v in link_graph.values())
        orphans = [d.id for d in docs if not link_graph.get(d.id) and not any(d.id in v for v in link_graph.values())]
        return {
            "note_count":  len(docs),
            "total_links": total_links,
            "orphan_notes": len(orphans),
            "avg_words":   int(sum(d.metadata["word_count"] for d in docs) / max(len(docs), 1)),
        }
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
