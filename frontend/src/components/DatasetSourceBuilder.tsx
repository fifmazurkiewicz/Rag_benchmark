import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { api } from "../api/client";

// Sources that already have QA pairs built-in (no generation needed)
const SOURCES_WITH_QA = new Set(["finqa", "medqa", "medmcqa"]);

// Extra config fields per source
const SOURCE_CONFIG: Record<string, { label: string; key: string; placeholder: string }[]> = {
  wikipedia:  [{ label: "Search query", key: "query", placeholder: "e.g. multiple sclerosis neurology" }],
  pubmed:     [{ label: "Search query", key: "query", placeholder: "e.g. neurology demyelination" }],
  football:   [],
  volleyball: [],
  finqa:      [{ label: "Max docs", key: "max_docs", placeholder: "200" }],
  medqa:      [
    { label: "Max docs",  key: "max_docs",  placeholder: "200" },
    { label: "Subtopic filter", key: "subtopic", placeholder: "e.g. neurology (optional)" },
  ],
  medmcqa:    [
    { label: "Max docs", key: "max_docs", placeholder: "200" },
    { label: "Subject filter", key: "subject", placeholder: "e.g. Neurology (optional)" },
  ],
};

const SOURCE_BADGES: Record<string, string> = {
  finqa:      "financial",
  medqa:      "medical",
  medmcqa:    "medical",
  wikipedia:  "general",
  pubmed:     "medical",
  football:   "sport",
  volleyball: "sport",
};

interface FormValues {
  source: string;
  dataset_name: string;
  generate_qa: boolean;
  qa_per_doc: number;
  [key: string]: unknown;
}

export default function DatasetSourceBuilder({ onBuilt }: { onBuilt: () => void }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);

  const { data: sources } = useQuery({
    queryKey: ["sources"],
    queryFn: api.listSources,
  });

  const { register, handleSubmit, watch, setValue } = useForm<FormValues>({
    defaultValues: { source: "wikipedia", dataset_name: "my_dataset", generate_qa: false, qa_per_doc: 3 },
  });

  const selectedSource = watch("source");
  const hasBuiltinQA   = SOURCES_WITH_QA.has(selectedSource);
  const extraFields    = SOURCE_CONFIG[selectedSource] ?? [];

  const mutation = useMutation({
    mutationFn: async (data: FormValues) => {
      const { source, dataset_name, generate_qa, qa_per_doc, ...rest } = data;
      const config: Record<string, unknown> = {};
      for (const field of SOURCE_CONFIG[source] ?? []) {
        if (rest[field.key]) config[field.key] = rest[field.key];
      }
      const res = await fetch("/api/datasets/from-source", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source, dataset_name, config, generate_qa, qa_per_doc }),
      });
      if (!res.ok) throw new Error(await res.text());
      return res.json();
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["datasets"] });
      setOpen(false);
      onBuilt();
    },
  });

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="px-4 py-2 bg-emerald-700 hover:bg-emerald-600 rounded text-sm font-medium transition-colors"
      >
        + Build from source
      </button>
    );
  }

  return (
    <div className="border border-emerald-700 rounded-xl p-5 bg-gray-900 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-emerald-300">Build dataset from source</h2>
        <button onClick={() => setOpen(false)} className="text-gray-500 hover:text-gray-300 text-sm">cancel</button>
      </div>

      {/* Source cards */}
      <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
        {(sources ?? []).map((s) => (
          <button
            key={s.name}
            type="button"
            onClick={() => setValue("source", s.name)}
            className={`rounded-lg p-2 text-left border transition-colors ${
              selectedSource === s.name
                ? "border-emerald-500 bg-emerald-900/30"
                : "border-gray-700 hover:border-gray-500"
            }`}
          >
            <div className="text-sm font-mono font-semibold text-gray-200">{s.name}</div>
            <div className={`text-xs mt-0.5 ${
              SOURCE_BADGES[s.name] === "financial" ? "text-yellow-400" :
              SOURCE_BADGES[s.name] === "medical"   ? "text-blue-400"   :
              SOURCE_BADGES[s.name] === "sport"     ? "text-green-400"  : "text-gray-400"
            }`}>
              {SOURCE_BADGES[s.name] ?? "general"}
            </div>
            {SOURCES_WITH_QA.has(s.name) && (
              <div className="text-xs text-emerald-400 mt-0.5">QA included</div>
            )}
          </button>
        ))}
      </div>

      <form onSubmit={handleSubmit((d) => mutation.mutate(d))} className="space-y-3">
        {/* Description */}
        {sources?.find((s) => s.name === selectedSource)?.description && (
          <p className="text-xs text-gray-400 italic">
            {sources.find((s) => s.name === selectedSource)?.description}
          </p>
        )}

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Dataset name</label>
            <input {...register("dataset_name", { required: true })} className="input text-sm" />
          </div>
          {extraFields.map((f) => (
            <div key={f.key}>
              <label className="label">{f.label}</label>
              <input {...register(f.key)} placeholder={f.placeholder} className="input text-sm" />
            </div>
          ))}
        </div>

        {!hasBuiltinQA && (
          <div className="flex items-center gap-4 p-3 bg-gray-800 rounded-lg">
            <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
              <input type="checkbox" {...register("generate_qa")} className="rounded" />
              Generate QA pairs via Claude
            </label>
            <div className="flex items-center gap-2">
              <label className="text-xs text-gray-500">per doc:</label>
              <input type="number" {...register("qa_per_doc", { valueAsNumber: true, min: 1, max: 10 })}
                className="input text-sm w-16" />
            </div>
          </div>
        )}

        {hasBuiltinQA && (
          <p className="text-xs text-emerald-400/80">
            This source includes ground-truth QA pairs — no generation needed.
          </p>
        )}

        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={mutation.isPending}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 rounded text-sm font-medium transition-colors"
          >
            {mutation.isPending ? "Building..." : "Build dataset"}
          </button>
          {mutation.isSuccess && <span className="text-sm text-emerald-400">Building in background…</span>}
          {mutation.isError && <span className="text-sm text-red-400">{String(mutation.error)}</span>}
        </div>
      </form>
    </div>
  );
}
