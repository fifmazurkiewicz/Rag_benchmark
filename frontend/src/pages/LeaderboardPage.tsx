import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { ExperimentResult, PipelineRunResult } from "../api/types";

const SCORE_METRICS = [
  "faithfulness",
  "answer_relevancy",
  "context_precision",
  "context_recall",
  "answer_correctness",
  "hit_rate",
];

const COST_METRICS = ["latency_p95"];

type SortDir = "asc" | "desc";

interface Row {
  run_id: string;
  experiment: string;
  dataset: string;
  pipeline_name: string;
  pipeline_type: string;
  avg_latency_ms: number;
  total_tokens: number;
  scores: Record<string, number>;
}

function metricColor(name: string, val: number): string {
  if (COST_METRICS.includes(name)) return "text-gray-300";
  if (val < 0) return "text-gray-600";
  if (val >= 0.7) return "text-green-400";
  if (val >= 0.4) return "text-yellow-400";
  return "text-red-400";
}

export default function LeaderboardPage() {
  const { data: runIds, isLoading } = useQuery({
    queryKey: ["results"],
    queryFn: api.listResults,
  });

  const { data: allResults } = useQuery({
    queryKey: ["all-results", runIds],
    queryFn: async () => {
      if (!runIds?.length) return [];
      return Promise.all(runIds.map((id) => api.getRunResult(id)));
    },
    enabled: !!runIds?.length,
  });

  const [datasetFilter, setDatasetFilter] = useState<string>("all");
  const [sortCol, setSortCol] = useState<string>("avg_latency_ms");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  const rows = useMemo<Row[]>(() => {
    if (!allResults) return [];
    return allResults.flatMap((result: ExperimentResult) =>
      result.pipeline_results.map((pr: PipelineRunResult) => ({
        run_id: result.run_id,
        experiment: result.experiment_name,
        dataset: result.dataset,
        pipeline_name: pr.pipeline_name,
        pipeline_type: pr.pipeline_type,
        avg_latency_ms: pr.avg_latency_ms,
        total_tokens: pr.total_tokens,
        scores: Object.fromEntries(pr.metrics.map((m) => [m.name, m.value])),
      }))
    );
  }, [allResults]);

  const datasets = useMemo(() => ["all", ...new Set(rows.map((r) => r.dataset))], [rows]);

  const allMetrics = useMemo(
    () => [...new Set(rows.flatMap((r) => Object.keys(r.scores)))],
    [rows]
  );

  const filtered = useMemo(
    () => (datasetFilter === "all" ? rows : rows.filter((r) => r.dataset === datasetFilter)),
    [rows, datasetFilter]
  );

  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      let av: number, bv: number;
      if (sortCol === "avg_latency_ms") { av = a.avg_latency_ms; bv = b.avg_latency_ms; }
      else if (sortCol === "total_tokens") { av = a.total_tokens; bv = b.total_tokens; }
      else { av = a.scores[sortCol] ?? -1; bv = b.scores[sortCol] ?? -1; }
      return sortDir === "asc" ? av - bv : bv - av;
    });
  }, [filtered, sortCol, sortDir]);

  function toggleSort(col: string) {
    if (sortCol === col) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortCol(col); setSortDir("desc"); }
  }

  function SortHeader({ col, label }: { col: string; label: string }) {
    const active = sortCol === col;
    return (
      <th
        className={`py-2 px-3 text-right cursor-pointer select-none whitespace-nowrap font-medium transition-colors ${
          active ? "text-indigo-300" : "text-gray-400 hover:text-gray-200"
        }`}
        onClick={() => toggleSort(col)}
      >
        {label}{active ? (sortDir === "desc" ? " ↓" : " ↑") : ""}
      </th>
    );
  }

  if (isLoading) {
    return <div className="text-center py-20 text-gray-500">Loading results…</div>;
  }

  if (!rows.length) {
    return (
      <div className="text-center py-20 text-gray-500">
        No results yet. Run an experiment first.
      </div>
    );
  }

  return (
    <div className="max-w-full mx-auto space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-2xl font-bold">Leaderboard</h1>

        <div className="flex items-center gap-3">
          <label className="text-sm text-gray-400">Dataset</label>
          <select
            value={datasetFilter}
            onChange={(e) => setDatasetFilter(e.target.value)}
            className="input text-sm"
          >
            {datasets.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="overflow-x-auto rounded-xl border border-gray-700">
        <table className="w-full text-sm">
          <thead className="border-b border-gray-700 bg-gray-900/80">
            <tr>
              <th className="py-2 px-3 text-left text-gray-400 font-medium whitespace-nowrap">Pipeline</th>
              <th className="py-2 px-3 text-left text-gray-400 font-medium whitespace-nowrap">Experiment</th>
              <th className="py-2 px-3 text-left text-gray-400 font-medium whitespace-nowrap">Dataset</th>
              <th className="py-2 px-3 text-left text-gray-400 font-medium whitespace-nowrap">Type</th>
              <SortHeader col="avg_latency_ms" label="Latency (ms)" />
              <SortHeader col="total_tokens" label="Tokens" />
              {allMetrics.map((m) => (
                <SortHeader key={m} col={m} label={m} />
              ))}
              <th className="py-2 px-3 text-gray-400 font-medium">Export</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((row, i) => (
              <tr
                key={`${row.run_id}-${row.pipeline_name}`}
                className={`border-b border-gray-800 hover:bg-gray-800/40 ${i === 0 && sortDir === "desc" ? "bg-indigo-950/30" : ""}`}
              >
                <td className="py-2 px-3 font-mono text-indigo-300 whitespace-nowrap">{row.pipeline_name}</td>
                <td className="py-2 px-3 text-gray-300 whitespace-nowrap">{row.experiment}</td>
                <td className="py-2 px-3 text-gray-400 whitespace-nowrap">{row.dataset}</td>
                <td className="py-2 px-3 text-gray-500 text-xs whitespace-nowrap">{row.pipeline_type}</td>
                <td className="py-2 px-3 text-right text-gray-300">{row.avg_latency_ms.toFixed(0)}</td>
                <td className="py-2 px-3 text-right text-gray-300">{row.total_tokens.toLocaleString()}</td>
                {allMetrics.map((m) => {
                  const val = row.scores[m] ?? -1;
                  return (
                    <td key={m} className={`py-2 px-3 text-right font-mono ${metricColor(m, val)}`}>
                      {val < 0 ? "—" : val.toFixed(3)}
                    </td>
                  );
                })}
                <td className="py-2 px-3 text-center">
                  <button
                    onClick={() => api.exportExcel(row.run_id)}
                    className="text-xs px-2 py-1 border border-gray-600 text-gray-400 hover:text-white hover:border-gray-400 rounded transition-colors"
                    title={`Download Excel for run ${row.run_id}`}
                  >
                    xlsx
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-gray-600">
        {sorted.length} pipeline run{sorted.length !== 1 ? "s" : ""} shown.
        Click column headers to sort. Green ≥ 0.7 · Yellow ≥ 0.4 · Red &lt; 0.4.
      </p>
    </div>
  );
}
