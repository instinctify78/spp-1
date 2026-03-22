"""HuggingFace Transformers inference backend.

Supports any AutoModelForCausalLM-compatible model on cuda / mps / cpu.
Tensor capture is done via PyTorch forward hooks (see collectors/tensor_hooks.py).
"""

import threading
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer

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

        # Attach tensor capture hooks if requested
        artifact_dir = Path(settings.data_dir) / "tensors"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        hook = TensorCaptureHook(config.capture_layers, artifact_dir)
        if config.capture_layers:
            hook.attach(self._model)

        # Reset memory counters before generation
        reset_memory_stats(self._device)

        # Streaming via TextIteratorStreamer (runs generate() in a thread)
        streamer = TextIteratorStreamer(
            self._tokenizer,
            skip_prompt=True,
            skip_special_tokens=True,
        )

        gen_kwargs = dict(
            **inputs,
            max_new_tokens=config.max_new_tokens,
            temperature=config.temperature,
            do_sample=config.do_sample,
            streamer=streamer,
        )

        gen_thread = threading.Thread(target=self._model.generate, kwargs=gen_kwargs, daemon=True)

        token_events: list[TokenEvent] = []
        ttft_ms: float = 0.0
        t_start = time.perf_counter()

        gen_thread.start()

        step = 0
        full_text = ""
        for token_str in streamer:
            elapsed_ms = (time.perf_counter() - t_start) * 1000
            if step == 0:
                ttft_ms = elapsed_ms

            # Approximate token_id via tokenizer (streamer doesn't expose ids directly)
            token_ids = self._tokenizer.encode(token_str, add_special_tokens=False)
            token_id = token_ids[0] if token_ids else -1

            token_events.append(TokenEvent(
                token=token_str,
                token_id=token_id,
                step=step,
                elapsed_ms=elapsed_ms,
            ))
            full_text += token_str
            step += 1

        gen_thread.join()

        total_latency_ms = (time.perf_counter() - t_start) * 1000
        peak_memory_mb = get_peak_memory_mb(self._device)
        tensor_artifacts = hook.detach() if config.capture_layers else {}

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
