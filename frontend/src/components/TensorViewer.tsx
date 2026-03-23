import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef } from "react";

interface TensorData {
  layer_name: string;
  shape: number[];
  vmin: number;
  vmax: number;
  data: number[][];
}

function heatmapColor(value: number): string {
  // Blue (0) → White (0.5) → Red (1)
  const r = Math.round(value < 0.5 ? value * 2 * 255 : 255);
  const b = Math.round(value > 0.5 ? (1 - value) * 2 * 255 : 255);
  const g = Math.round(value < 0.5 ? value * 2 * 200 : (1 - value) * 2 * 200);
  return `rgb(${r},${g},${b})`;
}

function HeatmapCanvas({ data, shape }: { data: number[][]; shape: number[] }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rows = data.length;
  const cols = data[0]?.length ?? 0;
  const cellSize = Math.max(2, Math.min(8, Math.floor(480 / cols)));
  const width = cols * cellSize;
  const height = rows * cellSize;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        ctx.fillStyle = heatmapColor(data[r][c]);
        ctx.fillRect(c * cellSize, r * cellSize, cellSize, cellSize);
      }
    }
  }, [data, rows, cols, cellSize]);

  return (
    <div className="overflow-x-auto">
      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        className="rounded border"
        title={`Shape: ${shape.join(" × ")}`}
      />
      <p className="text-xs text-muted-foreground mt-1">
        Shape: {shape.join(" × ")} &nbsp;·&nbsp; showing first {cols} cols
      </p>
    </div>
  );
}

export function TensorViewer({ runId, layerName }: { runId: number; layerName: string }) {
  const { data, isLoading, error } = useQuery<TensorData>({
    queryKey: ["tensor", runId, layerName],
    queryFn: async () => {
      const res = await fetch(`/runs/${runId}/tensors/${encodeURIComponent(layerName)}`);
      if (!res.ok) throw new Error("Failed to load tensor");
      return res.json();
    },
    staleTime: Infinity,
  });

  if (isLoading) return <div className="text-sm text-muted-foreground">Loading tensor…</div>;
  if (error || !data) return <div className="text-sm text-destructive">Failed to load tensor data.</div>;

  return (
    <div className="space-y-2">
      <div className="flex gap-4 text-xs text-muted-foreground">
        <span>min: {data.vmin.toFixed(4)}</span>
        <span>max: {data.vmax.toFixed(4)}</span>
      </div>
      <HeatmapCanvas data={data.data} shape={data.shape} />
    </div>
  );
}
