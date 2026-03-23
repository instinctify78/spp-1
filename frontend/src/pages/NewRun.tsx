import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation } from "@tanstack/react-query";
import { runsApi } from "@/api/runs";
import { systemApi } from "@/api/system";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function NewRun() {
  const navigate = useNavigate();

  const { data: devices = [] } = useQuery({
    queryKey: ["gpus"],
    queryFn: systemApi.gpus,
  });

  const [modelId, setModelId] = useState("gpt2");
  const [prompt, setPrompt] = useState("The capital of France is");
  const [device, setDevice] = useState("cpu");
  const [name, setName] = useState("");
  const [maxNewTokens, setMaxNewTokens] = useState(256);
  const [temperature, setTemperature] = useState(1.0);
  const [doSample, setDoSample] = useState(false);
  const [captureLayers, setCaptureLayers] = useState("");

  const { mutate: createRun, isPending, error } = useMutation({
    mutationFn: runsApi.create,
    onSuccess: (run) => navigate(`/runs/${run.id}`),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    createRun({
      name: name || undefined,
      model_id: modelId,
      prompt,
      device,
      max_new_tokens: maxNewTokens,
      temperature,
      do_sample: doSample,
      capture_layers: captureLayers
        ? captureLayers.split(",").map((s) => s.trim()).filter(Boolean)
        : [],
    });
  }

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">New Run</h1>
        <p className="text-sm text-muted-foreground mt-1">Configure and launch an inference run.</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Name */}
        <div className="space-y-1.5">
          <Label htmlFor="name">Run name (optional)</Label>
          <Input
            id="name"
            placeholder="e.g. llama-3.2-1B on MPS"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>

        {/* Model */}
        <div className="space-y-1.5">
          <Label htmlFor="model_id">Model ID *</Label>
          <Input
            id="model_id"
            required
            placeholder="gpt2 or meta-llama/Llama-3.2-1B"
            value={modelId}
            onChange={(e) => setModelId(e.target.value)}
          />
          <p className="text-xs text-muted-foreground">HuggingFace Hub ID or local path.</p>
        </div>

        {/* Prompt */}
        <div className="space-y-1.5">
          <Label htmlFor="prompt">Prompt *</Label>
          <textarea
            id="prompt"
            required
            rows={3}
            className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm
                       placeholder:text-muted-foreground focus-visible:outline-none
                       focus-visible:ring-2 focus-visible:ring-ring resize-none"
            placeholder="Enter your prompt…"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
          />
        </div>

        {/* Device */}
        <div className="space-y-1.5">
          <Label htmlFor="device">Device *</Label>
          <select
            id="device"
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm
                       focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            value={device}
            onChange={(e) => setDevice(e.target.value)}
          >
            {devices.length > 0 ? (
              devices.map((d) => (
                <option key={d.device} value={d.device}>
                  {d.name} ({d.device}){d.total_memory_mb ? ` — ${(d.total_memory_mb / 1024).toFixed(1)} GB` : ""}
                </option>
              ))
            ) : (
              <>
                <option value="cpu">CPU</option>
                <option value="cuda">CUDA (cuda:0)</option>
                <option value="mps">Apple MPS</option>
              </>
            )}
          </select>
        </div>

        {/* Max new tokens + temperature */}
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <Label htmlFor="max_new_tokens">Max new tokens</Label>
            <Input
              id="max_new_tokens"
              type="number"
              min={1}
              max={4096}
              value={maxNewTokens}
              onChange={(e) => setMaxNewTokens(Number(e.target.value))}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="temperature">Temperature</Label>
            <Input
              id="temperature"
              type="number"
              min={0}
              max={2}
              step={0.1}
              value={temperature}
              onChange={(e) => setTemperature(Number(e.target.value))}
            />
          </div>
        </div>

        {/* Capture layers */}
        <div className="space-y-1.5">
          <Label htmlFor="capture_layers">Capture layers (optional)</Label>
          <Input
            id="capture_layers"
            placeholder="e.g. transformer.h.0, transformer.h.11"
            value={captureLayers}
            onChange={(e) => setCaptureLayers(e.target.value)}
          />
          <p className="text-xs text-muted-foreground">
            Comma-separated layer names to capture activations for the heatmap.
            For gpt2 try: <code className="bg-muted px-1 rounded">transformer.h.0, transformer.h.11</code>
          </p>
        </div>

        {/* Sampling */}
        <div className="flex items-center gap-3">
          <input
            id="do_sample"
            type="checkbox"
            className="h-4 w-4 rounded border-input"
            checked={doSample}
            onChange={(e) => setDoSample(e.target.checked)}
          />
          <Label htmlFor="do_sample">Enable sampling (do_sample)</Label>
        </div>

        {error && (
          <div className="rounded-md bg-destructive/10 border border-destructive/20 px-4 py-3 text-sm text-destructive">
            {(error as Error).message}
          </div>
        )}

        <div className="flex gap-3 pt-2">
          <Button type="submit" disabled={isPending}>
            {isPending ? "Launching…" : "Launch Run"}
          </Button>
          <Button type="button" variant="outline" onClick={() => navigate("/")}>
            Cancel
          </Button>
        </div>
      </form>
    </div>
  );
}
