import type { ExperimentResult } from "../../api/types";
import MetricsTable from "./MetricsTable";
import RadarChart from "./RadarChart";

interface Props {
  results: ExperimentResult[];
}

export default function Dashboard({ results }: Props) {
  if (results.length === 0) {
    return (
      <div className="text-center py-20 text-gray-500">
        No results yet. Run an experiment first.
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {results.map((result) => (
        <div key={result.run_id} className="border border-gray-700 rounded-xl p-6 space-y-6 bg-gray-900">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-100">{result.experiment_name}</h2>
            <span className="text-xs font-mono text-gray-500">run: {result.run_id} | dataset: {result.dataset}</span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div>
              <h3 className="text-sm font-medium text-gray-400 mb-3">Metrics comparison</h3>
              <RadarChart result={result} />
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-400 mb-3">Score table</h3>
              <MetricsTable result={result} />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
