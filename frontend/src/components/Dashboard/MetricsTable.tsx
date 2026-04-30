import type { ExperimentResult } from "../../api/types";

interface Props {
  result: ExperimentResult;
}

export default function MetricsTable({ result }: Props) {
  const allMetrics = [
    ...new Set(result.pipeline_results.flatMap((p) => p.metrics.map((m) => m.name))),
  ];

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-700">
            <th className="text-left py-2 px-3 text-gray-400 font-medium">Pipeline</th>
            <th className="text-right py-2 px-3 text-gray-400 font-medium">Latency P95</th>
            <th className="text-right py-2 px-3 text-gray-400 font-medium">Tokens</th>
            {allMetrics.map((m) => (
              <th key={m} className="text-right py-2 px-3 text-gray-400 font-medium">{m}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {result.pipeline_results.map((pr) => (
            <tr key={pr.pipeline_name} className="border-b border-gray-800 hover:bg-gray-800/50">
              <td className="py-2 px-3 font-mono text-indigo-300">{pr.pipeline_name}</td>
              <td className="py-2 px-3 text-right text-gray-300">{pr.avg_latency_ms.toFixed(0)}ms</td>
              <td className="py-2 px-3 text-right text-gray-300">{pr.total_tokens.toLocaleString()}</td>
              {allMetrics.map((m) => {
                const metric = pr.metrics.find((x) => x.name === m);
                const val = metric?.value ?? -1;
                const isError = val < 0;
                return (
                  <td key={m} className={`py-2 px-3 text-right font-mono ${
                    isError ? "text-gray-600" : val >= 0.7 ? "text-green-400" : val >= 0.4 ? "text-yellow-400" : "text-red-400"
                  }`}>
                    {isError ? "—" : val.toFixed(3)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
