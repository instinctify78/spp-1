"""System info endpoints — available devices, GPU stats."""

import torch
from fastapi import APIRouter

router = APIRouter()


@router.get("/gpus")
def list_gpus():
    devices = [{"device": "cpu", "type": "cpu", "name": "CPU"}]

    if torch.cuda.is_available():
        for i in range(torch.cuda.device_count()):
            props = torch.cuda.get_device_properties(i)
            devices.append({
                "device": f"cuda:{i}",
                "type": "cuda",
                "name": props.name,
                "total_memory_mb": props.total_memory / (1024 ** 2),
            })

    if torch.backends.mps.is_available():
        devices.append({"device": "mps", "type": "mps", "name": "Apple MPS"})

    return {"devices": devices}
