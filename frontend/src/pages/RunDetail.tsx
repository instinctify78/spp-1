import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { runsApi } from "@/api/runs";
import type { Run, Metric } from "@/api/types";
import { StatusBadge } from "@/components/ui/badge";
import { StatCard } from "@/components/ui/stat-card";
import { Button } from "@/components/ui/button";

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

  const { data: run, isLoading, error } = useQuery<Run>({
    queryKey: ["runs", runId],
    queryFn: () => runsApi.get(runId),
    refetchInterval: (query) => {
      const data = query.state.data as Run | undefined;
      const active = data?.status === "PENDING" || data?.status === "RUNNING";
      return active ? 2000 : false;
    },
  });

  if (isLoading) return <div className="p-8 text-muted-foreground">Loading…</div>;
  if (error || !run) return <div className="p-8 text-destructive">Run not found.</div>;

  const cfg = run.config;
  const ttft     = findMetric(run.metrics, "ttft_ms");
  const latency  = findMetric(run.metrics, "total_latency_ms");
  const tps      = findMetric(run.metrics, "throughput_tps");
  const memory   = findMetric(run.metrics, "peak_memory_mb");
  const numToks  = findMetric(run.metrics, "num_tokens");
  const outputText = cfg.output_text as string | undefined;

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

      {/* Error */}
      {run.error && (
        <div className="rounded-md bg-destructive/10 border border-destructive/20 px-4 py-3 text-sm text-destructive">
          <strong>Error:</strong> {run.error}
        </div>
      )}

      {/* Metrics */}
      <div>
        <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wide mb-3">Performance</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <StatCard label="Throughput" value={fmt(tps)} unit="tok/s" />
          <StatCard label="Latency"    value={fmt(latency, 0)} unit="ms" />
          <StatCard label="TTFT"       value={fmt(ttft, 0)} unit="ms" />
          <StatCard label="Peak memory" value={fmt(memory, 0)} unit="MB" />
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-3">
          <StatCard label="Tokens generated" value={fmt(numToks, 0)} />
          <StatCard
            label="Finished"
            value={run.finished_at
              ? new Date(run.finished_at).toLocaleTimeString()
              : run.status === "RUNNING" ? "Running…" : "—"}
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

      {/* Output */}
      {(outputText || run.status === "RUNNING") && (
        <div>
          <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wide mb-3">Output</h2>
          <div className="rounded-lg border bg-muted/30 p-4 text-sm font-mono whitespace-pre-wrap min-h-[6rem]">
            {outputText ?? (
              <span className="text-muted-foreground animate-pulse">Generating…</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
