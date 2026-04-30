import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef } from "react";
import { api } from "../api/client";

export default function DatasetsPage() {
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);

  const { data: datasets, isLoading } = useQuery({
    queryKey: ["datasets"],
    queryFn: api.listDatasets,
  });

  const deleteMutation = useMutation({
    mutationFn: api.deleteDataset,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["datasets"] }),
  });

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch("/api/datasets/upload", { method: "POST", body: form });
      if (!res.ok) throw new Error(await res.text());
      return res.json();
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["datasets"] }),
  });

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Datasets</h1>
        <div className="flex gap-3">
          <input
            ref={fileRef}
            type="file"
            accept=".json"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) uploadMutation.mutate(file);
            }}
          />
          <button
            onClick={() => fileRef.current?.click()}
            disabled={uploadMutation.isPending}
            className="px-4 py-2 border border-indigo-700 text-indigo-400 hover:bg-indigo-900/50 rounded text-sm transition-colors disabled:opacity-50"
          >
            {uploadMutation.isPending ? "Uploading..." : "Upload JSON"}
          </button>
        </div>
      </div>

      <div className="border border-gray-700 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-800">
            <tr>
              <th className="text-left px-4 py-3 text-gray-400 font-medium">Name</th>
              <th className="text-right px-4 py-3 text-gray-400 font-medium">Documents</th>
              <th className="text-right px-4 py-3 text-gray-400 font-medium">QA pairs</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr><td colSpan={4} className="text-center py-8 text-gray-500">Loading...</td></tr>
            )}
            {!isLoading && !datasets?.length && (
              <tr><td colSpan={4} className="text-center py-8 text-gray-500">No datasets. Upload a JSON file.</td></tr>
            )}
            {datasets?.map((d) => (
              <tr key={d.name} className="border-t border-gray-800 hover:bg-gray-800/40">
                <td className="px-4 py-3 font-mono text-indigo-300">{d.name}</td>
                <td className="px-4 py-3 text-right text-gray-300">{d.doc_count}</td>
                <td className="px-4 py-3 text-right text-gray-300">{d.qa_count}</td>
                <td className="px-4 py-3 text-right">
                  <button
                    onClick={() => {
                      if (confirm(`Delete dataset '${d.name}'?`)) deleteMutation.mutate(d.name);
                    }}
                    className="text-xs text-red-400 hover:text-red-300"
                  >
                    delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="text-xs text-gray-500 space-y-1">
        <p>Expected JSON format:</p>
        <pre className="bg-gray-900 rounded p-3 text-gray-400 overflow-x-auto">{`{
  "documents": [{"id": "doc_1", "text": "...", "metadata": {}}],
  "qa_pairs":  [{"question": "...", "answer": "...", "doc_id": "doc_1"}]
}`}</pre>
      </div>
    </div>
  );
}
