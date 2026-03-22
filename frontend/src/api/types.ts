export type RunStatus = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";

export interface Metric {
  metric_type: string;
  value: number;
  step: number | null;
}

export interface Run {
  id: number;
  name: string | null;
  status: RunStatus;
  config: Record<string, unknown>;
  error: string | null;
  created_at: string;
  finished_at: string | null;
  metrics: Metric[];
}

export interface CreateRunPayload {
  name?: string;
  model_id: string;
  prompt: string;
  device: string;
  backend_type?: "huggingface";
  max_new_tokens?: number;
  temperature?: number;
  do_sample?: boolean;
  capture_layers?: string[];
}

export interface Device {
  device: string;
  type: string;
  name: string;
  total_memory_mb?: number;
}
