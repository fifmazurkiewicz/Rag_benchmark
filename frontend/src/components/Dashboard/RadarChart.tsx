import {
  RadarChart as RechartsRadar,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Legend,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import type { ExperimentResult } from "../../api/types";

const COLORS = ["#6366f1", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4"];

interface Props {
  result: ExperimentResult;
}

export default function RadarChart({ result }: Props) {
  const allMetrics = [
    ...new Set(
      result.pipeline_results.flatMap((p) =>
        p.metrics.filter((m) => m.value >= 0 && m.value <= 1).map((m) => m.name)
      )
    ),
  ];

  const data = allMetrics.map((metricName) => {
    const entry: Record<string, string | number> = { metric: metricName };
    for (const pr of result.pipeline_results) {
      const m = pr.metrics.find((x) => x.name === metricName);
      entry[pr.pipeline_name] = m && m.value >= 0 ? parseFloat(m.value.toFixed(3)) : 0;
    }
    return entry;
  });

  return (
    <ResponsiveContainer width="100%" height={320}>
      <RechartsRadar data={data}>
        <PolarGrid stroke="#374151" />
        <PolarAngleAxis dataKey="metric" tick={{ fill: "#9ca3af", fontSize: 11 }} />
        <PolarRadiusAxis domain={[0, 1]} tick={{ fill: "#4b5563", fontSize: 10 }} />
        <Tooltip
          contentStyle={{ backgroundColor: "#111827", border: "1px solid #374151", borderRadius: 6 }}
          labelStyle={{ color: "#e5e7eb" }}
        />
        <Legend wrapperStyle={{ fontSize: 12, color: "#9ca3af" }} />
        {result.pipeline_results.map((pr, i) => (
          <Radar
            key={pr.pipeline_name}
            name={pr.pipeline_name}
            dataKey={pr.pipeline_name}
            stroke={COLORS[i % COLORS.length]}
            fill={COLORS[i % COLORS.length]}
            fillOpacity={0.15}
          />
        ))}
      </RechartsRadar>
    </ResponsiveContainer>
  );
}
