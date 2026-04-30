from __future__ import annotations
import json
import pathlib
import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks
from backend.models.experiment import ExperimentConfig, RunStatus
from backend.models.result import ExperimentResult

router = APIRouter(prefix="/experiments", tags=["experiments"])

EXPERIMENTS_DIR = pathlib.Path("experiments")
EXPERIMENTS_DIR.mkdir(exist_ok=True)
RESULTS_DIR = pathlib.Path("results")
RESULTS_DIR.mkdir(exist_ok=True)

_active_runs: dict[str, RunStatus] = {}


@router.get("/", response_model=list[str])
def list_experiments():
    return [p.stem for p in EXPERIMENTS_DIR.glob("*.json")]


@router.get("/{name}")
def get_experiment(name: str):
    path = EXPERIMENTS_DIR / f"{name}.json"
    if not path.exists():
        raise HTTPException(404, f"Experiment '{name}' not found")
    return json.loads(path.read_text())


@router.post("/")
def save_experiment(config: ExperimentConfig):
    path = EXPERIMENTS_DIR / f"{config.name}.json"
    path.write_text(config.model_dump_json(indent=2))
    return {"saved": config.name}


@router.post("/{name}/run")
def run_experiment(name: str, background_tasks: BackgroundTasks):
    path = EXPERIMENTS_DIR / f"{name}.json"
    if not path.exists():
        raise HTTPException(404, f"Experiment '{name}' not found")
    config = ExperimentConfig.model_validate_json(path.read_text())
    run_id = str(uuid.uuid4())[:8]
    status = RunStatus(run_id=run_id, experiment_name=name, status="pending")
    _active_runs[run_id] = status
    background_tasks.add_task(_execute_run, run_id, config)
    return {"run_id": run_id}


@router.get("/runs/{run_id}", response_model=RunStatus)
def get_run_status(run_id: str):
    if run_id not in _active_runs:
        raise HTTPException(404, f"Run '{run_id}' not found")
    return _active_runs[run_id]


@router.get("/results/{run_id}")
def get_run_result(run_id: str):
    path = RESULTS_DIR / f"{run_id}.json"
    if not path.exists():
        raise HTTPException(404, f"Results for run '{run_id}' not found")
    return json.loads(path.read_text())


@router.get("/results/")
def list_results():
    return [p.stem for p in RESULTS_DIR.glob("*.json")]


async def _execute_run(run_id: str, config: ExperimentConfig):
    import asyncio
    import json as _json
    from backend.factory import build_pipeline
    from backend.datasets.loaders import load_dataset
    from backend.evaluation.engine import evaluate_pipeline

    run = _active_runs[run_id]
    run.status = "running"
    pipeline_results = []

    try:
        dataset = load_dataset(config.dataset)
        docs = dataset["documents"]
        qa_pairs = dataset["qa_pairs"]
        total = len(config.pipelines)

        for idx, pcfg in enumerate(config.pipelines):
            run.message = f"Running pipeline {pcfg.name} ({idx+1}/{total})"
            run.progress = idx / total

            cfg_dict = pcfg.model_dump()
            cfg_dict["pipeline"] = pcfg.pipeline
            pipeline = build_pipeline(cfg_dict)

            await pipeline.ingest(docs)
            answers = []
            for qa in qa_pairs:
                result = await pipeline.query(qa["question"])
                answers.append({
                    "question": qa["question"],
                    "ground_truth": qa["answer"],
                    "answer": result.answer,
                    "source_chunks": [c.text for c in result.source_chunks],
                    "latency_ms": result.latency_ms,
                    "tokens_used": result.tokens_used,
                })
            await pipeline.teardown()

            metrics = await evaluate_pipeline(answers, config.metrics)
            pipeline_results.append({
                "pipeline_name": pcfg.name,
                "pipeline_type": pcfg.pipeline,
                "metrics": metrics,
                "avg_latency_ms": sum(a["latency_ms"] for a in answers) / max(len(answers), 1),
                "total_tokens": sum(a["tokens_used"] for a in answers),
                "answers": answers,
            })

        result = ExperimentResult(
            experiment_name=config.name,
            run_id=run_id,
            dataset=config.dataset,
            pipeline_results=pipeline_results,
        )
        path = RESULTS_DIR / f"{run_id}.json"
        path.write_text(result.model_dump_json(indent=2))
        run.status = "done"
        run.progress = 1.0
        run.message = "Completed"

    except Exception as exc:
        run.status = "error"
        run.message = str(exc)
