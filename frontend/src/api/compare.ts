export interface CompareRun {
  id: number;
  name: string;
  model_id: string;
  device: string;
  status: string;
}

export interface MetricRow {
  label: string;
  lower_is_better: boolean;
  values: Record<string, number>;
  best_run_id: number;
  worst_run_id: number;
}

export interface CompareData {
  runs: CompareRun[];
  metrics: Record<string, MetricRow>;
}

export const compareApi = {
  compare: async (runIds: number[]): Promise<CompareData> => {
    const res = await fetch(`/compare?run_ids=${runIds.join(",")}`);
    if (!res.ok) throw new Error("Failed to fetch comparison");
    return res.json();
  },

  triggerBenchmark: async (runId: number, tasks: string[]): Promise<void> => {
    await fetch(`/runs/${runId}/benchmark`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tasks }),
    });
  },

  getBenchmarks: async (runId: number) => {
    const res = await fetch(`/runs/${runId}/benchmark`);
    return res.json();
  },
};
