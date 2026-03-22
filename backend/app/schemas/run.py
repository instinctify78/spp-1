from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class RunCreate(BaseModel):
    model_config = {"protected_namespaces": ()}

    name: str | None = None
    model_id: str = Field(..., examples=["gpt2", "meta-llama/Llama-3.2-1B"])
    prompt: str
    device: str = Field("cpu", examples=["cpu", "cuda", "cuda:0", "mps"])
    backend_type: Literal["huggingface"] = "huggingface"
    max_new_tokens: int = Field(256, ge=1, le=4096)
    temperature: float = Field(1.0, ge=0.0, le=2.0)
    do_sample: bool = False
    capture_layers: list[str] = Field(default_factory=list)


class MetricOut(BaseModel):
    metric_type: str
    value: float
    step: int | None

    model_config = {"from_attributes": True}


class RunOut(BaseModel):
    id: int
    name: str | None
    status: str
    config: dict
    error: str | None
    created_at: datetime
    finished_at: datetime | None
    metrics: list[MetricOut] = []

    model_config = {"from_attributes": True}
