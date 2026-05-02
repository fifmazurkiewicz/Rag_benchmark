import { useQuery } from "@tanstack/react-query";
import { useForm, useFieldArray } from "react-hook-form";
import { api } from "../../api/client";
import type { ExperimentConfig, PipelineConfig } from "../../api/types";
import { AVAILABLE_METRICS, DEFAULT_PIPELINE_CONFIG } from "../../api/types";
import PipelineRow from "./PipelineRow";

interface Props {
  initial?: Partial<ExperimentConfig>;
  onSubmit: (cfg: ExperimentConfig) => void;
  loading?: boolean;
}

export default function ConfigBuilder({ initial, onSubmit, loading }: Props) {
  const { data: registry } = useQuery({ queryKey: ["registry"], queryFn: api.getRegistry });
  const { data: datasets } = useQuery({ queryKey: ["datasets"], queryFn: api.listDatasets });

  const { register, control, handleSubmit, watch, setValue } = useForm<ExperimentConfig>({
    defaultValues: {
      name: initial?.name ?? "experiment_1",
      dataset: initial?.dataset ?? "",
      description: initial?.description ?? "",
      metrics: initial?.metrics ?? ["faithfulness", "answer_relevancy", "hit_rate", "latency_p95"],
      pipelines: initial?.pipelines ?? [{ ...DEFAULT_PIPELINE_CONFIG }],
    },
  });

  const { fields, append, remove } = useFieldArray({ control, name: "pipelines" });
  const selectedMetrics = watch("metrics");

  const toggleMetric = (m: string) => {
    const updated = selectedMetrics.includes(m)
      ? selectedMetrics.filter((x) => x !== m)
      : [...selectedMetrics, m];
    setValue("metrics", updated);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="label">Experiment name</label>
          <input {...register("name", { required: true })} className="input" />
        </div>
        <div>
          <label className="label">Dataset</label>
          <select {...register("dataset", { required: true })} className="input">
            <option value="">-- select --</option>
            {datasets?.map((d) => (
              <option key={d.name} value={d.name}>{d.name} ({d.qa_count} QA)</option>
            ))}
          </select>
        </div>
      </div>

      <div>
        <label className="label">Description</label>
        <input {...register("description")} className="input" placeholder="optional" />
      </div>

      <div>
        <label className="label">Metrics</label>
        <div className="flex flex-wrap gap-2 mt-1">
          {AVAILABLE_METRICS.map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => toggleMetric(m)}
              className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                selectedMetrics?.includes(m)
                  ? "bg-indigo-600 border-indigo-600 text-white"
                  : "border-gray-600 text-gray-400 hover:border-indigo-400"
              }`}
            >
              {m}
            </button>
          ))}
        </div>
        <input type="hidden" {...register("metrics")} />
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="label">Pipelines to compare</label>
          <button
            type="button"
            onClick={() => append({ ...DEFAULT_PIPELINE_CONFIG, name: `pipeline_${fields.length + 1}` })}
            className="text-xs text-indigo-400 hover:text-indigo-300 border border-indigo-700 px-3 py-1 rounded"
          >
            + Add pipeline
          </button>
        </div>
        {fields.map((field, idx) => (
          <PipelineRow
            key={field.id}
            index={idx}
            control={control}
            register={register}
            registry={registry}
            onRemove={() => remove(idx)}
            canRemove={fields.length > 1}
          />
        ))}
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded font-semibold transition-colors"
      >
        {loading ? "Saving..." : "Save & Run"}
      </button>
    </form>
  );
}
