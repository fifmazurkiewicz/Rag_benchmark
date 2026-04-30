from __future__ import annotations
from pydantic import BaseModel
from typing import Any


class MetricScore(BaseModel):
    name: str
    value: float
    details: dict[str, Any] = {}


class PipelineRunResult(BaseModel):
    pipeline_name: str
    pipeline_type: str
    metrics: list[MetricScore]
    avg_latency_ms: float
    total_tokens: int
    answers: list[dict[str, Any]] = []


class ExperimentResult(BaseModel):
    experiment_name: str
    run_id: str
    dataset: str
    pipeline_results: list[PipelineRunResult]
