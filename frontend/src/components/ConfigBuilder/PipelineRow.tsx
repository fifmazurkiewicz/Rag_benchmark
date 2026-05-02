import type { Control, UseFormRegister } from "react-hook-form";
import { useWatch } from "react-hook-form";
import type { ExperimentConfig, Registry } from "../../api/types";

interface Props {
  index: number;
  control: Control<ExperimentConfig>;
  register: UseFormRegister<ExperimentConfig>;
  registry?: Registry;
  onRemove: () => void;
  canRemove: boolean;
}

export default function PipelineRow({ index, control, register, registry, onRemove, canRemove }: Props) {
  const pipeline = useWatch({ control, name: `pipelines.${index}.pipeline` });
  const isGraphRAG = pipeline === "falkordb_graphrag";

  const field = (name: keyof import("../../api/types").PipelineConfig) =>
    `pipelines.${index}.${name}` as const;

  return (
    <div className="border border-gray-700 rounded-lg p-4 space-y-3 bg-gray-900">
      <div className="flex items-center justify-between">
        <input
          {...register(field("name"), { required: true })}
          className="input w-48 text-sm font-mono"
          placeholder="pipeline name"
        />
        {canRemove && (
          <button type="button" onClick={onRemove} className="text-red-400 hover:text-red-300 text-xs">
            remove
          </button>
        )}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        <div>
          <label className="label text-xs">Pipeline type</label>
          <select {...register(field("pipeline"))} className="input text-sm">
            {(registry?.pipeline ?? ["qdrant_dense", "chroma_dense", "falkordb_graphrag"]).map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </div>

        {!isGraphRAG && (
          <>
            <div>
              <label className="label text-xs">Chunker</label>
              <select {...register(field("chunker"))} className="input text-sm">
                {(registry?.chunker ?? ["fixed", "sentence", "recursive", "semantic", "markdown", "propositional"]).map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label text-xs">Chunk size</label>
              <input type="number" {...register(field("chunk_size"), { valueAsNumber: true })} className="input text-sm" />
            </div>
            <div>
              <label className="label text-xs">Overlap</label>
              <input type="number" {...register(field("overlap"), { valueAsNumber: true })} className="input text-sm" />
            </div>
          </>
        )}

        <div>
          <label className="label text-xs">Embedder</label>
          <select {...register(field("embedder_model"))} className="input text-sm">
            {(registry?.embedder ?? [
              "openrouter/text-embedding-3-small",
              "openrouter/text-embedding-3-large",
              "hf/bge-large-en",
              "hf/all-MiniLM-L6-v2",
            ]).map((e) => (
              <option key={e} value={e}>{e}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="label text-xs">LLM model</label>
          <input
            {...register(field("llm_model"))}
            className="input text-sm"
            placeholder="anthropic/claude-haiku-4-5-20251001"
          />
        </div>

        <div>
          <label className="label text-xs">Top K</label>
          <input type="number" {...register(field("top_k"), { valueAsNumber: true })} className="input text-sm" />
        </div>

        <div>
          <label className="label text-xs">Query transformer</label>
          <select {...register(field("query_transformer"))} className="input text-sm">
            {(registry?.query_transformer ?? ["none", "hyde"]).map((q) => (
              <option key={q} value={q}>{q}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="label text-xs">Reranker</label>
          <select {...register(field("reranker"))} className="input text-sm">
            {(registry?.reranker ?? ["none", "cross_encoder", "openrouter"]).map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        </div>
      </div>

      {isGraphRAG && (
        <p className="text-xs text-yellow-500/80 bg-yellow-900/20 px-3 py-2 rounded">
          FalkorDB GraphRAG manages chunking internally — chunker and chunk_size settings are ignored.
        </p>
      )}
    </div>
  );
}
