from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class GenerationConfig:
    model_id: str                       # HuggingFace hub ID or local path
    prompt: str
    device: str = "cpu"                 # "cpu" | "cuda" | "cuda:0" | "cuda:1" | "mps"
    max_new_tokens: int = 256
    temperature: float = 1.0
    do_sample: bool = False
    capture_layers: list[str] = field(default_factory=list)  # layer names for tensor hooks


@dataclass
class TokenEvent:
    token: str
    token_id: int
    step: int
    elapsed_ms: float   # wall time since generation started


@dataclass
class GenerationResult:
    text: str
    tokens: list[TokenEvent]
    tensor_artifacts: dict[str, str]    # layer_name -> .npy file path
    time_to_first_token_ms: float
    total_latency_ms: float
    peak_memory_mb: float
    num_tokens: int

    @property
    def throughput_tps(self) -> float:
        if self.total_latency_ms <= 0:
            return 0.0
        return self.num_tokens / (self.total_latency_ms / 1000)


class InferenceBackend(ABC):
    """Abstract base for all inference backends (HuggingFace, llama.cpp, vLLM, …)."""

    @abstractmethod
    def load_model(self, model_id: str, device: str) -> None:
        """Load model weights onto the target device."""

    @abstractmethod
    def generate(self, config: GenerationConfig) -> GenerationResult:
        """Run generation and return the full result with metrics."""

    @abstractmethod
    def unload_model(self) -> None:
        """Release model from memory."""

    # Context manager support for safe resource cleanup
    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.unload_model()
