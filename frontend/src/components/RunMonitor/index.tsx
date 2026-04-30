import { useEffect, useState } from "react";
import { createRunWebSocket } from "../../api/client";
import type { RunStatus } from "../../api/types";

interface Props {
  runId: string;
  onDone?: (runId: string) => void;
}

export default function RunMonitor({ runId, onDone }: Props) {
  const [status, setStatus] = useState<RunStatus | null>(null);

  useEffect(() => {
    const ws = createRunWebSocket(runId, (s) => {
      setStatus(s);
      if (s.status === "done" || s.status === "error") {
        onDone?.(runId);
      }
    });
    return () => ws.close();
  }, [runId, onDone]);

  if (!status) return <div className="text-gray-500 text-sm">Connecting...</div>;

  const statusColor = {
    pending: "text-gray-400",
    running: "text-yellow-400",
    done: "text-green-400",
    error: "text-red-400",
  }[status.status];

  return (
    <div className="border border-gray-700 rounded-lg p-4 space-y-3 bg-gray-900">
      <div className="flex items-center justify-between">
        <span className="font-mono text-sm text-gray-300">Run: {runId}</span>
        <span className={`text-sm font-semibold ${statusColor}`}>{status.status.toUpperCase()}</span>
      </div>

      <div className="w-full bg-gray-800 rounded-full h-2">
        <div
          className="bg-indigo-500 h-2 rounded-full transition-all duration-500"
          style={{ width: `${Math.round(status.progress * 100)}%` }}
        />
      </div>

      <p className="text-xs text-gray-400 min-h-[1rem]">{status.message}</p>

      {status.status === "error" && (
        <div className="text-xs text-red-300 bg-red-900/30 rounded p-2 font-mono break-all">
          {status.message}
        </div>
      )}
    </div>
  );
}
