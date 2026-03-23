import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import { runsApi } from "@/api/runs";
import { compareApi, type CompareData } from "@/api/compare";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const CHART_COLORS = ["#6366f1", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6", "#06b6d4"];

// Metric keys to show in bar chart (exclude large absolute values)
const CHART_METRICS = ["throughput_tps", "ttft_ms", "total_latency_ms", "peak_memory_mb", "perplexity"];

export default function Compare() {
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [compareData, setCompareData] = useState<CompareData | null>(null);
  const [loading, setLoading] = useState(false);

  const { data: runs = [] } = useQuery({
    queryKey: ["runs"],
    queryFn: runsApi.list,
  });

  const completedRuns = runs.filter((r) => r.status === "COMPLETED");

  function toggleRun(id: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
    setCompareData(null);
  }

  async function runComparison() {
    if (selectedIds.size < 1) return;
    setLoading(true);
    try {
      const data = await compareApi.compare([...selectedIds]);
      setCompareData(data);
    } finally {
      setLoading(false);
    }
  }

  function downloadCsv() {
    window.open(`/compare?run_ids=${[...selectedIds].join(",")}&format=csv`);
  }

  // Build chart data: [{metric, Run#1: val, Run#2: val}]
  const chartData = compareData
    ? Object.entries(compareData.metrics)
        .filter(([key]) => CHART_METRICS.includes(key))
        .map(([key, row]) => {
          const entry: Record<string, string | number> = { metric: row.label };
          compareData.runs.forEach((run) => {
            entry[run.name] = row.values[String(run.id)] ?? 0;
          });
          return entry;
        })
    : [];

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Compare Runs</h1>
          <p className="text-sm text-muted-foreground mt-1">Select completed runs to compare side by side.</p>
        </div>
        <div className="flex gap-2">
          {compareData && (
            <Button variant="outline" onClick={downloadCsv}>Export CSV</Button>
          )}
          <Button onClick={runComparison} disabled={selectedIds.size < 1 || loading}>
            {loading ? "Loading…" : "Compare"}
          </Button>
        </div>
      </div>

      {/* Run selector */}
      <div className="rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-muted-foreground">
            <tr>
              <th className="px-4 py-3 w-10" />
              <th className="px-4 py-3 text-left font-medium">Run</th>
              <th className="px-4 py-3 text-left font-medium">Model</th>
              <th className="px-4 py-3 text-left font-medium">Device</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {completedRuns.length === 0 && (
              <tr><td colSpan={4} className="px-4 py-8 text-center text-muted-foreground">No completed runs yet.</td></tr>
            )}
            {completedRuns.map((run) => (
              <tr
                key={run.id}
                className={cn("cursor-pointer transition-colors hover:bg-muted/30", selectedIds.has(run.id) && "bg-accent")}
                onClick={() => toggleRun(run.id)}
              >
                <td className="px-4 py-3">
                  <input type="checkbox" readOnly checked={selectedIds.has(run.id)} className="h-4 w-4 rounded" />
                </td>
                <td className="px-4 py-3 font-medium">{run.name ?? `Run #${run.id}`}</td>
                <td className="px-4 py-3 font-mono text-xs">{run.config.model_id as string}</td>
                <td className="px-4 py-3 font-mono text-xs">{run.config.device as string}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {compareData && (
        <>
          {/* Pivot table */}
          <div className="rounded-lg border overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 text-muted-foreground">
                <tr>
                  <th className="px-4 py-3 text-left font-medium">Metric</th>
                  {compareData.runs.map((run) => (
                    <th key={run.id} className="px-4 py-3 text-right font-medium">
                      <div>{run.name}</div>
                      <div className="font-mono text-xs font-normal">{run.device}</div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {Object.entries(compareData.metrics).map(([key, row]) => (
                  <tr key={key}>
                    <td className="px-4 py-3 text-muted-foreground">{row.label}</td>
                    {compareData.runs.map((run) => {
                      const val = row.values[String(run.id)];
                      const isBest  = run.id === row.best_run_id;
                      const isWorst = run.id === row.worst_run_id && compareData.runs.length > 1;
                      return (
                        <td
                          key={run.id}
                          className={cn(
                            "px-4 py-3 text-right tabular-nums font-mono",
                            isBest  && "text-green-700 font-semibold",
                            isWorst && "text-red-600",
                          )}
                        >
                          {val !== undefined ? val.toFixed(2) : "—"}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Bar chart */}
          {chartData.length > 0 && (
            <div>
              <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wide mb-3">Chart</h2>
              <div className="rounded-lg border p-4">
                <ResponsiveContainer width="100%" height={320}>
                  <BarChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 48 }}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                    <XAxis dataKey="metric" tick={{ fontSize: 11 }} angle={-25} textAnchor="end" />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Legend wrapperStyle={{ fontSize: 12, paddingTop: 16 }} />
                    {compareData.runs.map((run, i) => (
                      <Bar key={run.id} dataKey={run.name} fill={CHART_COLORS[i % CHART_COLORS.length]} radius={[3, 3, 0, 0]} />
                    ))}
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
