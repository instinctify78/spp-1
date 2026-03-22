from app.inference.base import InferenceBackend
from app.inference.hf_backend import HFBackend


def create_backend(backend_type: str) -> InferenceBackend:
    """Return an InferenceBackend instance for the given backend_type string."""
    match backend_type.lower():
        case "huggingface" | "hf":
            return HFBackend()
        case _:
            raise ValueError(f"Unknown backend type: {backend_type!r}. Supported: 'huggingface'")
