export interface Registry {
  pipeline: string[];
  chunker: string[];
  embedder: string[];
  vector_store: string[];
}

export interface PipelineConfig {
  name: string;
  pipeline: string;
  chunker: string;
  chunk_size: number;
  overlap: number;
  embedder_model: string;
  llm_model: string;
  top_k: number;
  extra: Record<string, unknown>;
}

export interface ExperimentConfig {
  name: string;
  dataset: string;
  pipelines: PipelineConfig[];
  metrics: string[];
  description: string;
}

export interface RunStatus {
  run_id: string;
  experiment_name: string;
  status: "pending" | "running" | "done" | "error";
  progress: number;
  message: string;
}

export interface MetricScore {
  name: string;
  value: number;
  details: Record<string, unknown>;
}

export interface PipelineRunResult {
  pipeline_name: string;
  pipeline_type: string;
  metrics: MetricScore[];
  avg_latency_ms: number;
  total_tokens: number;
  answers: QAAnswer[];
}

export interface QAAnswer {
  question: string;
  ground_truth: string;
  answer: string;
  source_chunks: string[];
  latency_ms: number;
  tokens_used: number;
}

export interface ExperimentResult {
  experiment_name: string;
  run_id: string;
  dataset: string;
  pipeline_results: PipelineRunResult[];
}

export interface DatasetMeta {
  name: string;
  doc_count: number;
  qa_count: number;
}

export const AVAILABLE_METRICS = [
  "faithfulness",
  "answer_relevancy",
  "context_precision",
  "context_recall",
  "answer_correctness",
  "hallucination",
  "hit_rate",
  "latency_p95",
] as const;

export const DEFAULT_PIPELINE_CONFIG: PipelineConfig = {
  name: "pipeline_1",
  pipeline: "qdrant_dense",
  chunker: "fixed",
  chunk_size: 512,
  overlap: 64,
  embedder_model: "openai/text-embedding-3-small",
  llm_model: "claude-haiku-4-5-20251001",
  top_k: 5,
  extra: {},
};
