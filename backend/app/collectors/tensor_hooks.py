"""PyTorch forward hooks for capturing intermediate layer activations.

Tensors are detached, moved to CPU, and saved as .npy files to avoid
holding large tensors in VRAM after the forward pass.
"""

from pathlib import Path

import numpy as np
import torch
import torch.nn as nn


class TensorCaptureHook:
    def __init__(self, layer_names: list[str], output_dir: Path) -> None:
        self.layer_names = set(layer_names)
        self.output_dir = output_dir
        self._handles: list[torch.utils.hooks.RemovableHook] = []
        self._captured: dict[str, str] = {}  # layer_name -> file path

    def attach(self, model: nn.Module) -> None:
        """Register hooks on all named modules that match layer_names."""
        for name, module in model.named_modules():
            if name in self.layer_names:
                handle = module.register_forward_hook(self._make_hook(name))
                self._handles.append(handle)

    def _make_hook(self, name: str):
        def hook(module: nn.Module, input, output):
            # output may be a tensor or a tuple; handle both
            tensor = output[0] if isinstance(output, tuple) else output
            if not isinstance(tensor, torch.Tensor):
                return
            arr = tensor.detach().cpu().float().numpy()
            path = self.output_dir / f"{name.replace('.', '_')}.npy"
            np.save(path, arr)
            self._captured[name] = str(path)
        return hook

    def detach(self) -> dict[str, str]:
        """Remove all hooks and return {layer_name: file_path} mapping."""
        for handle in self._handles:
            handle.remove()
        self._handles.clear()
        return dict(self._captured)
