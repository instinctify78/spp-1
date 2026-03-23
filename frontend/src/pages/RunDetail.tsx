import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { runsApi } from "@/api/runs";
import type { Run, Metric } from "@/api/types";
import { StatusBadge } from "@/components/ui/badge";
import { StatCard } from "@/components/ui/stat-card";
import { Button } from "@/components/ui/button";
import { StreamingOutput } from "@/components/StreamingOutput";
import { TensorViewer } from "@/components/TensorViewer";
import { useRunStream } from "@/hooks/useRunStream";

function findMetric(metrics: Metric[], type: string): number | null {
  return metrics.find((m) => m.metric_type === type)?.value ?? null;
}

function fmt(value: number | null, decimals = 1): string {
  if (value === null) return "—";
  return value.toFixed(decimals);
}

function ConfigRow({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="flex gap-2 text-sm">
      <span className="text-muted-foreground w-36 shrink-0">{label}</span>
      <span className="font-mono break-all">{String(value)}</span>
    </div>
  );
}

export default function RunDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const runId = Number(id);
  const [selectedLayer, setSelectedLayer] = useState<string | null>(null);

  const { data: run, isLoading, error } = useQuery<Run>({
    queryKey: ["runs", runId],
    queryFn: () => runsApi.get(runId),
    refetchInterval: (query) => {
      const data = query.state.data as Run | undefined;
      return data?.status === "PENDING" || data?.status === "RUNNING" ? 2000 : false;
    },
  });

  const isActive = run?.status === "PENDING" || run?.status === "RUNNING";
  const { text: streamText, done: streamDone } = useRunStream(runId, isActive ?? false);

  // Tensor layer list (only when completed)
  const { data: tensors = [] } = useQuery<{ layer_name: string }[]>({
    queryKey: ["tensors", runId],
    queryFn: async () => {
      const res = await fetch(`/runs/${runId}/tensors`);
      return res.json();
    },
    enabled: run?.status === "COMPLETED",
    staleTime: Infinity,
  });

  if (isLoading) return <div className="p-8 text-muted-foreground">Loading…</div>;
  if (error || !run) return <div className="p-8 text-destructive">Run not found.</div>;

  const cfg = run.config;
  const outputText = (cfg.output_text as string | undefined) ?? (streamDone ? streamText : undefined);

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold">{run.name ?? `Run #${run.id}`}</h1>
            <StatusBadge status={run.status} />
          </div>
          <p className="text-sm text-muted-foreground font-mono">{cfg.model_id as string}</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => navigate("/")}>← Back</Button>
      </div>

      {run.error && (
        <div className="rounded-md bg-destructive/10 border border-destructive/20 px-4 py-3 text-sm text-destructive">
          <strong>Error:</strong> {run.error}
        </div>
      )}

      {/* Metrics */}
      <div>
        <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wide mb-3">Performance</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <StatCard label="Throughput"   value={fmt(findMetric(run.metrics, "throughput_tps"))}   unit="tok/s" />
          <StatCard label="Latency"      value={fmt(findMetric(run.metrics, "total_latency_ms"), 0)} unit="ms" />
          <StatCard label="TTFT"         value={fmt(findMetric(run.metrics, "ttft_ms"), 0)}        unit="ms" />
          <StatCard label="Peak memory"  value={fmt(findMetric(run.metrics, "peak_memory_mb"), 0)} unit="MB" />
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-3">
          <StatCard label="Tokens generated" value={fmt(findMetric(run.metrics, "num_tokens"), 0)} />
          <StatCard
            label="Finished"
            value={run.finished_at
              ? new Date(run.finished_at).toLocaleTimeString()
              : isActive ? "Running…" : "—"}
          />
        </div>
      </div>

      {/* Config */}
      <div>
        <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wide mb-3">Configuration</h2>
        <div className="rounded-lg border p-4 space-y-2">
          <ConfigRow label="Device"         value={cfg.device} />
          <ConfigRow label="Backend"        value={cfg.backend_type ?? "huggingface"} />
          <ConfigRow label="Max new tokens" value={cfg.max_new_tokens} />
          <ConfigRow label="Temperature"    value={cfg.temperature} />
          <ConfigRow label="Do sample"      value={String(cfg.do_sample)} />
        </div>
      </div>

      {/* Prompt */}
      <div>
        <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wide mb-3">Prompt</h2>
        <div className="rounded-lg border bg-muted/30 p-4 text-sm font-mono whitespace-pre-wrap">
          {cfg.prompt as string}
        </div>
      </div>

      {/* Output — streaming while active, static when done */}
      {(isActive || outputText) && (
        <div>
          <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wide mb-3">Output</h2>
          {isActive
            ? <StreamingOutput text={streamText} done={streamDone} />
            : <div className="rounded-lg border bg-muted/30 p-4 text-sm font-mono whitespace-pre-wrap">{outputText}</div>
          }
        </div>
      )}

      {/* Tensor viewer */}
      {tensors.length > 0 && (
        <div>
          <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wide mb-3">
            Tensor Activations
          </h2>
          <div className="flex gap-2 flex-wrap mb-4">
            {tensors.map((t) => (
              <button
                key={t.layer_name}
                onClick={() => setSelectedLayer(t.layer_name === selectedLayer ? null : t.layer_name)}
                className={`px-3 py-1.5 rounded-md text-xs font-mono border transition-colors ${
                  selectedLayer === t.layer_name
                    ? "bg-primary text-primary-foreground border-primary"
                    : "bg-background hover:bg-accent border-input"
                }`}
              >
                {t.layer_name}
              </button>
            ))}
          </div>
          {selectedLayer && (
            <div className="rounded-lg border p-4">
              <TensorViewer runId={runId} layerName={selectedLayer} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
