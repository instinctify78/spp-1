"""HuggingFace Transformers inference backend.

Supports any AutoModelForCausalLM-compatible model on cuda / mps / cpu.
Uses a manual token-by-token generation loop so each token can be streamed
to the WebSocket via token_callback before the full result is returned.
"""

import time
from pathlib import Path
from typing import Callable

import torch
import torch.nn.functional as F
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

    def generate(
        self,
        config: GenerationConfig,
        token_callback: Callable[[TokenEvent], None] | None = None,
    ) -> GenerationResult:
        if self._model is None or self._tokenizer is None:
            self.load_model(config.model_id, config.device)

        inputs = self._tokenizer(config.prompt, return_tensors="pt").to(self._device)
        input_ids = inputs["input_ids"]
        attention_mask = inputs["attention_mask"]

        # Attach tensor capture hooks if requested
        artifact_dir = Path(settings.data_dir) / "tensors"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        hook = TensorCaptureHook(config.capture_layers, artifact_dir)
        if config.capture_layers:
            hook.attach(self._model)

        reset_memory_stats(self._device)

        eos_id = self._tokenizer.eos_token_id
        token_events: list[TokenEvent] = []
        ttft_ms: float = 0.0
        t_start = time.perf_counter()

        generated_ids = input_ids

        for step in range(config.max_new_tokens):
            with torch.no_grad():
                outputs = self._model(generated_ids, attention_mask=attention_mask)

            logits = outputs.logits[:, -1, :]  # [1, vocab_size]

            if config.do_sample and config.temperature > 0:
                logits = logits / config.temperature
                probs = F.softmax(logits, dim=-1)
                next_token = torch.multinomial(probs, num_samples=1)
            else:
                next_token = torch.argmax(logits, dim=-1, keepdim=True)

            token_id = next_token[0, 0].item()
            elapsed_ms = (time.perf_counter() - t_start) * 1000

            if step == 0:
                ttft_ms = elapsed_ms

            token_str = self._tokenizer.decode([token_id], skip_special_tokens=True)
            event = TokenEvent(token=token_str, token_id=token_id, step=step, elapsed_ms=elapsed_ms)
            token_events.append(event)

            if token_callback is not None:
                token_callback(event)

            if token_id == eos_id:
                break

            generated_ids = torch.cat([generated_ids, next_token], dim=1)
            attention_mask = torch.cat(
                [attention_mask, torch.ones((1, 1), device=self._device, dtype=attention_mask.dtype)],
                dim=1,
            )

        total_latency_ms = (time.perf_counter() - t_start) * 1000
        peak_memory_mb = get_peak_memory_mb(self._device)
        tensor_artifacts = hook.detach() if config.capture_layers else {}

        full_text = "".join(e.token for e in token_events)

        return GenerationResult(
            text=full_text,
            tokens=token_events,
            tensor_artifacts=tensor_artifacts,
            time_to_first_token_ms=ttft_ms,
            total_latency_ms=total_latency_ms,
            peak_memory_mb=peak_memory_mb,
            num_tokens=len(token_events),
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
