import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { api } from "../api/client";

interface VaultForm {
  vault_path: string;
  dataset_name: string;
  generate_qa: boolean;
  qa_per_note: number;
}

interface VaultStats {
  note_count: number;
  total_links: number;
  orphan_notes: number;
  avg_words: number;
}

export default function DatasetsPage() {
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [showVaultForm, setShowVaultForm] = useState(false);
  const [vaultStats, setVaultStats] = useState<VaultStats | null>(null);

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

  const vaultMutation = useMutation({
    mutationFn: async (data: VaultForm) => {
      const res = await fetch("/api/datasets/from-vault", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...data, excluded_folders: [] }),
      });
      if (!res.ok) throw new Error(await res.text());
      return res.json();
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["datasets"] });
      setShowVaultForm(false);
      setVaultStats(null);
    },
  });

  const { register, handleSubmit, watch } = useForm<VaultForm>({
    defaultValues: { vault_path: "", dataset_name: "my_vault", generate_qa: false, qa_per_note: 3 },
  });

  const vaultPath = watch("vault_path");

  async function checkVaultStats() {
    if (!vaultPath) return;
    try {
      const res = await fetch(`/api/datasets/vault/stats?vault_path=${encodeURIComponent(vaultPath)}`);
      if (res.ok) setVaultStats(await res.json());
    } catch {
      setVaultStats(null);
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Datasets</h1>
        <div className="flex gap-3">
          <button
            onClick={() => { setShowVaultForm(!showVaultForm); setVaultStats(null); }}
            className="px-4 py-2 bg-violet-700 hover:bg-violet-600 rounded text-sm font-medium transition-colors"
          >
            Import Obsidian Vault
          </button>
          <input ref={fileRef} type="file" accept=".json" className="hidden"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) uploadMutation.mutate(f); }} />
          <button
            onClick={() => fileRef.current?.click()}
            disabled={uploadMutation.isPending}
            className="px-4 py-2 border border-indigo-700 text-indigo-400 hover:bg-indigo-900/50 rounded text-sm transition-colors disabled:opacity-50"
          >
            {uploadMutation.isPending ? "Uploading..." : "Upload JSON"}
          </button>
        </div>
      </div>

      {/* Obsidian Vault Import Form */}
      {showVaultForm && (
        <div className="border border-violet-700 rounded-xl p-5 bg-gray-900 space-y-4">
          <div className="flex items-center gap-2">
            <span className="text-lg">🔮</span>
            <h2 className="font-semibold text-violet-300">Import Obsidian Vault</h2>
            <span className="text-xs text-gray-500 ml-1">Karpathy-style second brain RAG</span>
          </div>

          <form onSubmit={handleSubmit((d) => vaultMutation.mutate(d))} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-400 block mb-1">Vault path</label>
                <div className="flex gap-2">
                  <input
                    {...register("vault_path", { required: true })}
                    placeholder="/home/user/MyVault"
                    className="input text-sm flex-1"
                  />
                  <button
                    type="button"
                    onClick={checkVaultStats}
                    className="px-3 py-2 text-xs border border-gray-600 hover:border-violet-500 rounded transition-colors"
                  >
                    Check
                  </button>
                </div>
              </div>
              <div>
                <label className="text-xs text-gray-400 block mb-1">Dataset name</label>
                <input {...register("dataset_name", { required: true })} className="input text-sm" />
              </div>
            </div>

            {/* Vault stats preview */}
            {vaultStats && (
              <div className="grid grid-cols-4 gap-3 p-3 bg-violet-900/20 rounded-lg border border-violet-800/50">
                <div className="text-center">
                  <div className="text-lg font-bold text-violet-300">{vaultStats.note_count}</div>
                  <div className="text-xs text-gray-500">notes</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-bold text-violet-300">{vaultStats.total_links}</div>
                  <div className="text-xs text-gray-500">wikilinks</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-bold text-gray-400">{vaultStats.orphan_notes}</div>
                  <div className="text-xs text-gray-500">orphans</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-bold text-violet-300">{vaultStats.avg_words}</div>
                  <div className="text-xs text-gray-500">avg words</div>
                </div>
              </div>
            )}

            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
                <input type="checkbox" {...register("generate_qa")} className="rounded" />
                Generate QA pairs via Claude
              </label>
              <div className="flex items-center gap-2">
                <label className="text-xs text-gray-500">QA per note:</label>
                <input
                  type="number"
                  {...register("qa_per_note", { valueAsNumber: true, min: 1, max: 10 })}
                  className="input text-sm w-16"
                />
              </div>
            </div>

            <div className="flex gap-3">
              <button
                type="submit"
                disabled={vaultMutation.isPending}
                className="px-4 py-2 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 rounded text-sm font-medium transition-colors"
              >
                {vaultMutation.isPending ? "Importing..." : "Import vault"}
              </button>
              {vaultMutation.isSuccess && (
                <span className="text-sm text-green-400 self-center">Import started in background</span>
              )}
              {vaultMutation.isError && (
                <span className="text-sm text-red-400 self-center">{String(vaultMutation.error)}</span>
              )}
            </div>
          </form>

          <div className="text-xs text-gray-600 space-y-0.5 pt-1 border-t border-gray-800">
            <p>Parses: YAML frontmatter · [[wikilinks]] graph · #tags · headings</p>
            <p>Pipeline: obsidian_rag — uses backlink graph expansion at query time</p>
          </div>
        </div>
      )}

      {/* Dataset table */}
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
              <tr><td colSpan={4} className="text-center py-8 text-gray-500">No datasets yet.</td></tr>
            )}
            {datasets?.map((d) => (
              <tr key={d.name} className="border-t border-gray-800 hover:bg-gray-800/40">
                <td className="px-4 py-3 font-mono text-indigo-300">{d.name}</td>
                <td className="px-4 py-3 text-right text-gray-300">{d.doc_count}</td>
                <td className="px-4 py-3 text-right text-gray-300">{d.qa_count}</td>
                <td className="px-4 py-3 text-right">
                  <button
                    onClick={() => { if (confirm(`Delete '${d.name}'?`)) deleteMutation.mutate(d.name); }}
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

      <div className="text-xs text-gray-600 space-y-1">
        <p>JSON format: <code className="text-gray-500">{"{ documents: [{id, text, metadata}], qa_pairs: [{question, answer, doc_id}] }"}</code></p>
      </div>
    </div>
  );
}
