import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import RunMonitor from "../components/RunMonitor";
import { api } from "../api/client";
import MetricsTable from "../components/Dashboard/MetricsTable";
import RadarChart from "../components/Dashboard/RadarChart";

export default function RunPage() {
  const { runId } = useParams<{ runId: string }>();
  const navigate = useNavigate();
  const [isDone, setIsDone] = useState(false);

  const { data: result, refetch } = useQuery({
    queryKey: ["result", runId],
    queryFn: () => api.getRunResult(runId!),
    enabled: isDone,
  });

  if (!runId) return null;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <button onClick={() => navigate("/")} className="text-gray-400 hover:text-white text-sm">
          ← Back
        </button>
        <h1 className="text-2xl font-bold">Run Monitor</h1>
      </div>

      <RunMonitor
        runId={runId}
        onDone={() => {
          setIsDone(true);
          refetch();
        }}
      />

      {result && (
        <div className="border border-gray-700 rounded-xl p-6 space-y-6 bg-gray-900">
          <h2 className="text-lg font-semibold">Results: {result.experiment_name}</h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div>
              <h3 className="text-sm font-medium text-gray-400 mb-3">Radar</h3>
              <RadarChart result={result} />
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-400 mb-3">Scores</h3>
              <MetricsTable result={result} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
