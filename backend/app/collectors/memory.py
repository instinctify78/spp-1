"""Memory usage collectors for CUDA, MPS, and CPU."""

import psutil
import torch


def reset_memory_stats(device: str) -> None:
    """Reset peak memory tracking before a generation run."""
    if device.startswith("cuda"):
        torch.cuda.reset_peak_memory_stats(device)
    elif device == "mps":
        # MPS doesn't expose peak reset; nothing to do
        pass


def get_peak_memory_mb(device: str) -> float:
    """Return peak memory used (MB) for the given device."""
    if device.startswith("cuda"):
        return torch.cuda.max_memory_allocated(device) / (1024 ** 2)
    elif device == "mps":
        # torch.mps.current_allocated_memory is in bytes
        try:
            return torch.mps.current_allocated_memory() / (1024 ** 2)
        except AttributeError:
            return 0.0
    else:
        # CPU: report current process RSS as a proxy
        proc = psutil.Process()
        return proc.memory_info().rss / (1024 ** 2)
