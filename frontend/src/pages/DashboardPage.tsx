import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import Dashboard from "../components/Dashboard";
import type { ExperimentResult } from "../api/types";

export default function DashboardPage() {
  const { data: runIds } = useQuery({ queryKey: ["results"], queryFn: api.listResults });

  const results = useQuery({
    queryKey: ["all-results", runIds],
    queryFn: async () => {
      if (!runIds?.length) return [];
      return Promise.all(runIds.map((id) => api.getRunResult(id)));
    },
    enabled: !!runIds?.length,
  });

  return (
    <div className="max-w-6xl mx-auto space-y-4">
      <h1 className="text-2xl font-bold">Dashboard</h1>
      <Dashboard results={(results.data ?? []) as ExperimentResult[]} />
    </div>
  );
}
