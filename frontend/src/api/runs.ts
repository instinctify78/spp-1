import type { CreateRunPayload, Run } from "./types";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const runsApi = {
  list: () => apiFetch<Run[]>("/runs"),

  get: (id: number) => apiFetch<Run>(`/runs/${id}`),

  create: (payload: CreateRunPayload) =>
    apiFetch<Run>("/runs", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
