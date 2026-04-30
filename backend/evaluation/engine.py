from __future__ import annotations
from typing import Any


async def evaluate_pipeline(
    answers: list[dict[str, Any]],
    metrics: list[str],
) -> list[dict[str, Any]]:
    """
    Run requested metrics over a list of QA answers.
    Falls back gracefully when optional deps (ragas, deepeval) are not installed.
    """
    results = []
    for metric_name in metrics:
        try:
            score = await _run_metric(metric_name, answers)
            results.append({"name": metric_name, "value": score, "details": {}})
        except Exception as exc:
            results.append({"name": metric_name, "value": -1.0, "details": {"error": str(exc)}})
    return results


async def _run_metric(name: str, answers: list[dict[str, Any]]) -> float:
    _ragas = {"faithfulness", "answer_relevancy", "context_precision", "context_recall", "answer_correctness"}
    _deepeval = {"hallucination", "bias", "toxicity", "geval"}

    if name in _ragas:
        return await _ragas_metric(name, answers)
    if name in _deepeval:
        return await _deepeval_metric(name, answers)
    if name == "hit_rate":
        return _hit_rate(answers)
    if name == "latency_p95":
        return _latency_p95(answers)
    raise ValueError(f"Unknown metric: {name}")


async def _ragas_metric(name: str, answers: list[dict[str, Any]]) -> float:
    from ragas import evaluate as ragas_evaluate
    from ragas.metrics import (
        faithfulness, answer_relevancy,
        context_precision, context_recall, answer_correctness,
    )
    from datasets import Dataset

    _metric_map = {
        "faithfulness": faithfulness,
        "answer_relevancy": answer_relevancy,
        "context_precision": context_precision,
        "context_recall": context_recall,
        "answer_correctness": answer_correctness,
    }
    data = {
        "question": [a["question"] for a in answers],
        "answer": [a["answer"] for a in answers],
        "contexts": [a.get("source_chunks", []) for a in answers],
        "ground_truth": [a.get("ground_truth", "") for a in answers],
    }
    ds = Dataset.from_dict(data)
    result = ragas_evaluate(ds, metrics=[_metric_map[name]])
    return float(result[name])


async def _deepeval_metric(name: str, answers: list[dict[str, Any]]) -> float:
    from deepeval import evaluate as deval_evaluate
    from deepeval.test_case import LLMTestCase
    from deepeval.metrics import (
        HallucinationMetric, BiasMetric, ToxicityMetric, GEval,
    )

    _metric_cls = {
        "hallucination": lambda: HallucinationMetric(threshold=0.5),
        "bias": lambda: BiasMetric(threshold=0.5),
        "toxicity": lambda: ToxicityMetric(threshold=0.5),
        "geval": lambda: GEval(name="Correctness", criteria="Is the answer correct?", threshold=0.5),
    }
    metric = _metric_cls[name]()
    cases = [
        LLMTestCase(
            input=a["question"],
            actual_output=a["answer"],
            expected_output=a.get("ground_truth", ""),
            retrieval_context=a.get("source_chunks", []),
        )
        for a in answers
    ]
    scores = []
    for case in cases:
        metric.measure(case)
        scores.append(metric.score)
    return sum(scores) / len(scores) if scores else 0.0


def _hit_rate(answers: list[dict[str, Any]]) -> float:
    hits = 0
    for a in answers:
        gt = a.get("ground_truth", "").lower()
        if any(gt[:50] in chunk.lower() for chunk in a.get("source_chunks", [])):
            hits += 1
    return hits / len(answers) if answers else 0.0


def _latency_p95(answers: list[dict[str, Any]]) -> float:
    latencies = sorted(a.get("latency_ms", 0) for a in answers)
    if not latencies:
        return 0.0
    idx = int(len(latencies) * 0.95)
    return latencies[min(idx, len(latencies) - 1)]
