import { useState } from "react";
import type { PipelineConfig } from "../api/types";

interface Props {
  pipelines: PipelineConfig[];
}

// ── Step definitions ─────────────────────────────────────────────────────────

interface Step {
  label: string;
  value: string;
  note?: string;
  color: string;
}

function stepsFromConfig(cfg: PipelineConfig): Step[] {
  const isGraph = cfg.pipeline === "falkordb_graphrag" || cfg.pipeline === "neo4j_graphrag";
  const hasHyde = cfg.query_transformer && cfg.query_transformer !== "none";
  const hasReranker = cfg.reranker && cfg.reranker !== "none";

  const steps: Step[] = [];

  if (!isGraph) {
    // Ingest path
    steps.push({ label: "Chunker", value: cfg.chunker ?? "fixed", note: `size ${cfg.chunk_size}, overlap ${cfg.overlap}`, color: "bg-violet-900/60 border-violet-700" });
    steps.push({ label: "Embedder", value: cfg.embedder_model ?? "—", color: "bg-blue-900/60 border-blue-700" });
    steps.push({ label: "Vector store", value: cfg.pipeline.replace("_dense", "").replace("_hybrid", ""), color: "bg-cyan-900/60 border-cyan-700" });
  } else {
    steps.push({ label: "GraphRAG", value: cfg.pipeline, note: "monolithic SDK", color: "bg-amber-900/60 border-amber-700" });
  }

  steps.push({ label: "▼  Query path", value: "", color: "bg-transparent border-transparent text-gray-600" });

  if (hasHyde) {
    steps.push({ label: "Query transformer", value: cfg.query_transformer, note: `model: ${cfg.llm_model ?? "—"}`, color: "bg-fuchsia-900/60 border-fuchsia-700" });
  }

  if (!isGraph) {
    steps.push({ label: "Embedder", value: cfg.embedder_model ?? "—", note: "query embed", color: "bg-blue-900/60 border-blue-700" });
    steps.push({
      label: "Retrieve",
      value: cfg.pipeline.includes("hybrid") ? "hybrid" : "dense",
      note: `top ${hasReranker ? (cfg.retrieve_k || (cfg.top_k * 4)) : cfg.top_k}`,
      color: "bg-cyan-900/60 border-cyan-700",
    });
  }

  if (hasReranker) {
    steps.push({ label: "Reranker", value: cfg.reranker, note: `→ top ${cfg.top_k}`, color: "bg-orange-900/60 border-orange-700" });
  }

  steps.push({ label: "LLM", value: cfg.llm_model ?? "—", color: "bg-emerald-900/60 border-emerald-700" });

  return steps;
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function PipelineVisualizer({ pipelines }: Props) {
  const [view, setView] = useState<"diagram" | "json">("diagram");
  const [selected, setSelected] = useState(0);

  const cfg = pipelines[selected];
  if (!cfg) return null;

  const steps = stepsFromConfig(cfg).filter((s) => s.value !== "");

  return (
    <div className="space-y-3">
      {/* Pipeline selector tabs */}
      {pipelines.length > 1 && (
        <div className="flex gap-1 flex-wrap">
          {pipelines.map((p, i) => (
            <button
              key={p.name}
              onClick={() => setSelected(i)}
              className={`px-3 py-1 rounded text-xs font-mono transition-colors ${
                i === selected
                  ? "bg-indigo-600 text-white"
                  : "bg-gray-800 text-gray-400 hover:text-white"
              }`}
            >
              {p.name}
            </button>
          ))}
        </div>
      )}

      {/* View toggle */}
      <div className="flex gap-1">
        {(["diagram", "json"] as const).map((v) => (
          <button
            key={v}
            onClick={() => setView(v)}
            className={`px-3 py-1 rounded text-xs transition-colors ${
              view === v
                ? "bg-gray-700 text-white"
                : "text-gray-500 hover:text-gray-300"
            }`}
          >
            {v}
          </button>
        ))}
      </div>

      {view === "diagram" ? (
        <div className="flex flex-wrap items-center gap-1">
          {steps.map((step, i) => (
            <div key={i} className="flex items-center gap-1">
              <div className={`border rounded-lg px-3 py-2 text-xs ${step.color}`}>
                <div className="text-gray-400 font-medium leading-none mb-1">{step.label}</div>
                <div className="text-white font-mono truncate max-w-[180px]" title={step.value}>
                  {step.value}
                </div>
                {step.note && (
                  <div className="text-gray-500 text-[10px] mt-0.5">{step.note}</div>
                )}
              </div>
              {i < steps.length - 1 && (
                <span className="text-gray-600 text-xs select-none">→</span>
              )}
            </div>
          ))}
        </div>
      ) : (
        <pre className="bg-gray-950 border border-gray-800 rounded-lg p-4 text-xs text-gray-300 overflow-x-auto leading-relaxed">
          {JSON.stringify(cfg, null, 2)}
        </pre>
      )}
    </div>
  );
}
