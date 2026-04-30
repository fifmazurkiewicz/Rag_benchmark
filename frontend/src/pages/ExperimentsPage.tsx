import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { ExperimentConfig } from "../api/types";
import ConfigBuilder from "../components/ConfigBuilder";

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
            <div
              key={name}
              className="flex items-center justify-between border border-gray-700 rounded-lg px-4 py-3 bg-gray-900 hover:border-gray-600"
            >
              <span className="font-mono text-indigo-300">{name}</span>
              <button
                onClick={() => runMutation.mutate(name)}
                disabled={runMutation.isPending}
                className="text-sm px-3 py-1 border border-indigo-700 text-indigo-400 hover:bg-indigo-900/50 rounded transition-colors disabled:opacity-50"
              >
                Run
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
