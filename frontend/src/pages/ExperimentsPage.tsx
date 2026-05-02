import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { ExperimentConfig } from "../api/types";
import ConfigBuilder from "../components/ConfigBuilder";
import PipelineVisualizer from "../components/PipelineVisualizer";

export default function ExperimentsPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [view, setView] = useState<"list" | "new">("list");

  const { data: experiments } = useQuery({
    queryKey: ["experiments"],
    queryFn: api.listExperiments,
  });

  const saveMutation = useMutation({
    mutationFn: async (cfg: ExperimentConfig) => {
      await api.saveExperiment(cfg);
      const { run_id } = await api.runExperiment(cfg.name);
      return run_id;
    },
    onSuccess: (runId) => {
      qc.invalidateQueries({ queryKey: ["experiments"] });
      navigate(`/run/${runId}`);
    },
  });

  const runMutation = useMutation({
    mutationFn: (name: string) => api.runExperiment(name),
    onSuccess: ({ run_id }) => navigate(`/run/${run_id}`),
  });

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Experiments</h1>
        <button
          onClick={() => setView(view === "new" ? "list" : "new")}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded font-medium text-sm transition-colors"
        >
          {view === "new" ? "Cancel" : "+ New Experiment"}
        </button>
      </div>

      {view === "new" && (
        <div className="border border-gray-700 rounded-xl p-6 bg-gray-900">
          <h2 className="text-lg font-semibold mb-4">Configure new experiment</h2>
          <ConfigBuilder
            onSubmit={(cfg) => saveMutation.mutate(cfg)}
            loading={saveMutation.isPending}
          />
        </div>
      )}

      {view === "list" && (
        <div className="space-y-2">
          {!experiments?.length && (
            <div className="text-center py-12 text-gray-500">
              No experiments yet. Create one above.
            </div>
          )}
          {experiments?.map((name) => (
            <ExperimentRow
              key={name}
              name={name}
              onRun={() => runMutation.mutate(name)}
              running={runMutation.isPending}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function ExperimentRow({ name, onRun, running }: { name: string; onRun: () => void; running: boolean }) {
  const [expanded, setExpanded] = useState(false);
  const { data: cfg } = useQuery({
    queryKey: ["experiment", name],
    queryFn: () => api.getExperiment(name),
    enabled: expanded,
  });

  return (
    <div className="border border-gray-700 rounded-lg bg-gray-900 hover:border-gray-600 transition-colors">
      <div className="flex items-center justify-between px-4 py-3">
        <button
          onClick={() => setExpanded((e) => !e)}
          className="flex items-center gap-2 font-mono text-indigo-300 hover:text-indigo-200"
        >
          <span className="text-gray-600 text-xs">{expanded ? "▼" : "▶"}</span>
          {name}
        </button>
        <button
          onClick={onRun}
          disabled={running}
          className="text-sm px-3 py-1 border border-indigo-700 text-indigo-400 hover:bg-indigo-900/50 rounded transition-colors disabled:opacity-50"
        >
          Run
        </button>
      </div>

      {expanded && cfg && (
        <div className="border-t border-gray-800 px-4 py-3 space-y-2">
          <div className="text-xs text-gray-500">
            dataset: <span className="text-gray-300">{cfg.dataset}</span>
            {cfg.description && <span className="ml-3 italic">{cfg.description}</span>}
          </div>
          <PipelineVisualizer pipelines={cfg.pipelines} />
        </div>
      )}
    </div>
  );
}
