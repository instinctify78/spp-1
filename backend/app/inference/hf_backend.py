"""HuggingFace Transformers inference backend.

Supports any AutoModelForCausalLM-compatible model on cuda / mps / cpu.
Tensor capture is done via PyTorch forward hooks (see collectors/tensor_hooks.py).
Note: token-level streaming is added in Phase 3 via WebSockets.
"""

import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from app.collectors.memory import get_peak_memory_mb, reset_memory_stats
from app.collectors.tensor_hooks import TensorCaptureHook
from app.config import settings
from app.inference.base import GenerationConfig, GenerationResult, InferenceBackend, TokenEvent


class HFBackend(InferenceBackend):
    def __init__(self) -> None:
        self._model = None
        self._tokenizer = None
        self._device: str = "cpu"
        self._model_id: str = ""

    def load_model(self, model_id: str, device: str) -> None:
        self._model_id = model_id
        self._device = device

        self._tokenizer = AutoTokenizer.from_pretrained(model_id)

        torch_dtype = torch.float16 if device != "cpu" else torch.float32
        self._model = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype=torch_dtype,
            low_cpu_mem_usage=True,
        ).to(device)
        self._model.eval()

    def generate(self, config: GenerationConfig) -> GenerationResult:
        if self._model is None or self._tokenizer is None:
            self.load_model(config.model_id, config.device)

        inputs = self._tokenizer(config.prompt, return_tensors="pt").to(self._device)
        prompt_len = inputs["input_ids"].shape[1]

        # Attach tensor capture hooks if requested
        artifact_dir = Path(settings.data_dir) / "tensors"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        hook = TensorCaptureHook(config.capture_layers, artifact_dir)
        if config.capture_layers:
            hook.attach(self._model)

        reset_memory_stats(self._device)
        t_start = time.perf_counter()

        with torch.no_grad():
            output_ids = self._model.generate(
                **inputs,
                max_new_tokens=config.max_new_tokens,
                temperature=config.temperature,
                do_sample=config.do_sample,
            )

        total_latency_ms = (time.perf_counter() - t_start) * 1000
        peak_memory_mb = get_peak_memory_mb(self._device)
        tensor_artifacts = hook.detach() if config.capture_layers else {}

        # Decode only the newly generated tokens (exclude prompt)
        new_ids = output_ids[0][prompt_len:]
        full_text = self._tokenizer.decode(new_ids, skip_special_tokens=True)
        num_tokens = len(new_ids)

        # Build per-token events with estimated elapsed time (linear interpolation)
        token_events: list[TokenEvent] = []
        for step, token_id in enumerate(new_ids.tolist()):
            elapsed_ms = total_latency_ms * (step + 1) / num_tokens if num_tokens > 0 else 0
            token_events.append(TokenEvent(
                token=self._tokenizer.decode([token_id], skip_special_tokens=True),
                token_id=token_id,
                step=step,
                elapsed_ms=elapsed_ms,
            ))

        ttft_ms = token_events[0].elapsed_ms if token_events else 0.0

        return GenerationResult(
            text=full_text,
            tokens=token_events,
            tensor_artifacts=tensor_artifacts,
            time_to_first_token_ms=ttft_ms,
            total_latency_ms=total_latency_ms,
            peak_memory_mb=peak_memory_mb,
            num_tokens=num_tokens,
        )

    def unload_model(self) -> None:
        if self._model is not None:
            del self._model
            self._model = None
        if self._tokenizer is not None:
            del self._tokenizer
            self._tokenizer = None
        if self._device.startswith("cuda"):
            torch.cuda.empty_cache()
