from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any


class PipelineConfig(BaseModel):
    name: str
    pipeline: str
    chunker: str = "fixed"
    chunk_size: int = 512
    overlap: int = 64
    embedder_model: str = "openai/text-embedding-3-small"
    llm_model: str = "claude-haiku-4-5-20251001"
    top_k: int = 5
    extra: dict[str, Any] = Field(default_factory=dict)


class ExperimentConfig(BaseModel):
    name: str
    dataset: str
    pipelines: list[PipelineConfig]
    metrics: list[str] = Field(default_factory=lambda: [
        "faithfulness", "answer_relevancy", "context_precision", "context_recall"
    ])
    description: str = ""


class RunStatus(BaseModel):
    run_id: str
    experiment_name: str
    status: str  # pending | running | done | error
    progress: float = 0.0
    message: str = ""
