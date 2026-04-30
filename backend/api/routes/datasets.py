from __future__ import annotations
import json
import pathlib
from fastapi import APIRouter, UploadFile, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/datasets", tags=["datasets"])

DATASETS_DIR = pathlib.Path("datasets_store")
DATASETS_DIR.mkdir(exist_ok=True)


class DatasetMeta(BaseModel):
    name: str
    doc_count: int
    qa_count: int


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
