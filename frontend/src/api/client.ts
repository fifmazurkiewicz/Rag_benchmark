import type {
  Registry, ExperimentConfig, RunStatus,
  ExperimentResult, DatasetMeta,
} from "./types";

const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  // Registry
  getRegistry: () => request<Registry>("/registry/"),

  // Experiments
  listExperiments: () => request<string[]>("/experiments/"),
  getExperiment: (name: string) => request<ExperimentConfig>(`/experiments/${name}`),
  saveExperiment: (config: ExperimentConfig) =>
    request<{ saved: string }>("/experiments/", { method: "POST", body: JSON.stringify(config) }),
  runExperiment: (name: string) =>
    request<{ run_id: string }>(`/experiments/${name}/run`, { method: "POST" }),
  getRunStatus: (runId: string) => request<RunStatus>(`/experiments/runs/${runId}`),
  getRunResult: (runId: string) => request<ExperimentResult>(`/experiments/results/${runId}`),
  listResults: () => request<string[]>("/experiments/results/"),

  // Dataset sources
  listSources: () => request<{ name: string; description: string }[]>("/datasets/sources/"),

  // Datasets
  listDatasets: () => request<DatasetMeta[]>("/datasets/"),
  getDataset: (name: string) => request<unknown>(`/datasets/${name}`),
  deleteDataset: (name: string) =>
    request<{ deleted: string }>(`/datasets/${name}`, { method: "DELETE" }),
};

export function createRunWebSocket(
  runId: string,
  onMessage: (status: RunStatus) => void,
  onClose?: () => void
): WebSocket {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${window.location.host}/ws/runs/${runId}`);
  ws.onmessage = (e) => onMessage(JSON.parse(e.data) as RunStatus);
  ws.onclose = onClose ?? (() => {});
  return ws;
}
