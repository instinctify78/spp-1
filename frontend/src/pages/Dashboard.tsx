import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { runsApi } from "@/api/runs";
import type { Run } from "@/api/types";
import { StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

function metricValue(run: Run, type: string): string {
  const m = run.metrics.find((m) => m.metric_type === type);
  if (!m) return "—";
  return m.value.toFixed(type === "throughput_tps" ? 1 : 0);
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    month: "short", day: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

export default function Dashboard() {
  const navigate = useNavigate();

  const { data: runs = [], isLoading, error } = useQuery({
    queryKey: ["runs"],
    queryFn: runsApi.list,
    refetchInterval: (query) => {
      const data = query.state.data as Run[] | undefined;
      const hasActive = data?.some((r) => r.status === "PENDING" || r.status === "RUNNING");
      return hasActive ? 5000 : false;
    },
  });

  if (isLoading) return <div className="p-8 text-muted-foreground">Loading runs…</div>;
  if (error) return <div className="p-8 text-destructive">Failed to load runs.</div>;

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Runs</h1>
          <p className="text-sm text-muted-foreground mt-1">{runs.length} total</p>
        </div>
        <Button onClick={() => navigate("/runs/new")}>+ New Run</Button>
      </div>

      {runs.length === 0 ? (
        <div className="rounded-lg border border-dashed p-12 text-center text-muted-foreground">
          No runs yet. Create one to get started.
        </div>
      ) : (
        <div className="rounded-lg border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-muted-foreground">
              <tr>
                <th className="px-4 py-3 text-left font-medium">ID</th>
                <th className="px-4 py-3 text-left font-medium">Name / Model</th>
                <th className="px-4 py-3 text-left font-medium">Device</th>
                <th className="px-4 py-3 text-left font-medium">Status</th>
                <th className="px-4 py-3 text-right font-medium">Tokens/s</th>
                <th className="px-4 py-3 text-right font-medium">Latency (ms)</th>
                <th className="px-4 py-3 text-right font-medium">Mem (MB)</th>
                <th className="px-4 py-3 text-left font-medium">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {runs.map((run) => (
                <tr
                  key={run.id}
                  className="hover:bg-muted/30 cursor-pointer transition-colors"
                  onClick={() => navigate(`/runs/${run.id}`)}
                >
                  <td className="px-4 py-3 tabular-nums text-muted-foreground">#{run.id}</td>
                  <td className="px-4 py-3">
                    <div className="font-medium">{run.name ?? (run.config.model_id as string)}</div>
                    {run.name && (
                      <div className="text-xs text-muted-foreground">{run.config.model_id as string}</div>
                    )}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">{run.config.device as string}</td>
                  <td className="px-4 py-3"><StatusBadge status={run.status} /></td>
                  <td className="px-4 py-3 text-right tabular-nums">{metricValue(run, "throughput_tps")}</td>
                  <td className="px-4 py-3 text-right tabular-nums">{metricValue(run, "total_latency_ms")}</td>
                  <td className="px-4 py-3 text-right tabular-nums">{metricValue(run, "peak_memory_mb")}</td>
                  <td className="px-4 py-3 text-muted-foreground text-xs">{formatDate(run.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
