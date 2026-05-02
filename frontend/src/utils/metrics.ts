const COST_METRICS = new Set(["latency_p95"]);

export function metricScoreColor(name: string, value: number): string {
  if (COST_METRICS.has(name)) return "text-gray-300";
  if (value < 0) return "text-gray-600";
  if (value >= 0.7) return "text-green-400";
  if (value >= 0.4) return "text-yellow-400";
  return "text-red-400";
}
