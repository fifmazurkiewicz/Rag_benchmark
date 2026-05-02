"""
Experiment execution service.

Separated from the HTTP route so the orchestration logic is testable
and reusable without FastAPI context.
"""
from __future__ import annotations

import logging
from typing import Any

from backend.models.experiment import ExperimentConfig, PipelineConfig, RunStatus
from backend.models.result import ExperimentResult, PipelineRunResult, MetricScore

logger = logging.getLogger(__name__)


async def execute_experiment(run_id: str, config: ExperimentConfig, run: RunStatus) -> ExperimentResult:
    """
    Run all pipelines in the experiment sequentially.

    Updates `run` in-place so callers (e.g. WebSocket broadcaster) see live progress.
    Raises on unrecoverable errors; caller is responsible for setting run.status = "error".
    """
    from backend.factory import build_pipeline
    from backend.datasets.loaders import load_dataset
    from backend.evaluation.engine import evaluate_pipeline

    run.status = "running"
    pipeline_results: list[dict[str, Any]] = []

    dataset = load_dataset(config.dataset)
    docs = dataset["documents"]
    qa_pairs = dataset["qa_pairs"]
    total = len(config.pipelines)

    for idx, pcfg in enumerate(config.pipelines):
        run.message = f"Pipeline {pcfg.name} ({idx + 1}/{total})"
        run.progress = idx / total
        logger.info("run=%s pipeline=%s (%d/%d)", run_id, pcfg.name, idx + 1, total)

        result = await _run_single_pipeline(pcfg, docs, qa_pairs)
        metrics = await evaluate_pipeline(result["answers"], config.metrics)

        pipeline_results.append({
            "pipeline_name": pcfg.name,
            "pipeline_type": pcfg.pipeline,
            "config": pcfg.model_dump(),
            "metrics": [m if isinstance(m, dict) else m.model_dump() for m in metrics],
            "avg_latency_ms": _avg(result["answers"], "latency_ms"),
            "total_tokens": sum(a["tokens_used"] for a in result["answers"]),
            "answers": result["answers"],
        })

    run.progress = 1.0
    run.message = "Completed"
    run.status = "done"

    return ExperimentResult(
        experiment_name=config.name,
        run_id=run_id,
        dataset=config.dataset,
        pipeline_results=pipeline_results,
    )


async def _run_single_pipeline(
    pcfg: PipelineConfig,
    docs: list,
    qa_pairs: list[dict],
) -> dict[str, Any]:
    from backend.factory import build_pipeline

    cfg_dict = pcfg.model_dump()
    cfg_dict["pipeline"] = pcfg.pipeline
    pipeline = build_pipeline(cfg_dict)

    await pipeline.ingest(docs)
    answers = []
    for qa in qa_pairs:
        result = await pipeline.query(qa["question"])
        answers.append({
            "question": qa["question"],
            "ground_truth": qa.get("answer", ""),
            "answer": result.answer,
            "source_chunks": [c.text for c in result.source_chunks],
            "latency_ms": result.latency_ms,
            "tokens_used": result.tokens_used,
            "metadata": result.metadata,
        })
    await pipeline.teardown()
    return {"answers": answers}


def _avg(items: list[dict], key: str) -> float:
    values = [item[key] for item in items]
    return sum(values) / len(values) if values else 0.0
