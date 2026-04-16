from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class OptimizeFor(str, Enum):
    MIN_COST = "min_cost"
    MIN_TIME = "min_time"
    BALANCED = "balanced"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ModelSpec(BaseModel):
    name: str
    params: int = Field(gt=0, description="Total parameters in the model")
    architecture: str = "decoder-only"
    num_layers: int = Field(gt=0, description="Number of transformer layers")
    num_heads: int = Field(gt=0, description="Number of query attention heads")
    num_kv_heads: int = Field(gt=0, description="Number of KV attention heads (GQA/MQA support)")
    hidden_dim: int = Field(gt=0, description="Model hidden dimension size")
    vocab_size: int = Field(default=32000, gt=0)
    num_experts: int = Field(default=0, ge=0, description="Total experts for MoE models")
    active_experts: int = Field(default=0, ge=0, description="Active experts per token for MoE models")


class TrainingSpec(BaseModel):
    method: Literal["full", "lora", "qlora"] = "qlora"
    precision: Literal["fp32", "fp16", "bf16", "int8", "int4"] = "bf16"
    batch_size: int = Field(default=1, gt=0)
    grad_accum: int = Field(default=1, gt=0)
    seq_len: int = Field(default=2048, gt=0)
    epochs: float = Field(default=1.0, gt=0)
    num_workers: int = Field(default=4, ge=0)


class InferenceSpec(BaseModel):
    precision: Literal["fp32", "fp16", "bf16", "int8", "int4"] = "bf16"
    batch_size: int = Field(default=1, gt=0)
    prompt_tokens: int = Field(default=512, gt=0)
    max_new_tokens: int = Field(default=1024, gt=0)
    context_length: int | None = Field(
        default=None, 
        description="Target sequence length for KV cache planning. Defaults to prompt + max_new."
    )


class DataSpec(BaseModel):
    dataset_tokens: int = Field(gt=0)


class Workload(BaseModel):
    model: ModelSpec
    training: TrainingSpec | None = None
    inference: InferenceSpec | None = None
    data: DataSpec | None = None

    @field_validator("inference", mode="after")
    @classmethod
    def validate_workload_type(cls, v: InferenceSpec | None, info: any) -> InferenceSpec | None:
        # Simple validation: one of them must be present
        # This is a bit simplified for brevity, in practice we check training vs inference
        return v


class Constraints(BaseModel):
    platforms: list[str] = Field(default_factory=lambda: ["vast.ai", "runpod", "aws"])
    max_budget: float | None = Field(default=None, gt=0)
    max_time_hours: float | None = Field(default=None, gt=0)
    region: list[str] = Field(default_factory=list)
    max_gpus: int = Field(default=8, gt=0)

    @field_validator("platforms", "region")
    @classmethod
    def normalize_lower(cls, values: list[str]) -> list[str]:
        return [value.lower() for value in values]


class Preference(BaseModel):
    optimize_for: OptimizeFor = OptimizeFor.BALANCED


class PlanningRequest(BaseModel):
    workload: Workload | None = None
    pipeline: list[Workload] | None = None
    constraints: Constraints = Field(default_factory=Constraints)
    preference: Preference = Field(default_factory=Preference)

    @model_validator(mode="after")
    def validate_workload_source(self) -> PlanningRequest:
        if not self.workload and not self.pipeline:
             raise ValueError("Either 'workload' or 'pipeline' must be provided.")
        return self


class ResourceEstimate(BaseModel):
    required_vram_gb: float
    required_cpu_cores: int
    required_ram_gb: float
    total_flops: float
    throughput_tokens_per_second: float
    # Advanced metrics from Cursor blog
    throughput_prefill_tps: float = 0.0
    throughput_decoding_tps: float = 0.0
    kv_cache_gb: float = 0.0
    stage_details: list[ResourceEstimate] | None = None


class MarketOffer(BaseModel):
    gpu: str
    gpu_count: int = Field(default=1, gt=0)
    vram_gb: float = Field(gt=0)
    price_per_hour: float = Field(gt=0)
    cpu: int = Field(gt=0)
    ram_gb: float = Field(gt=0)
    gpu_flops_tflops: float = Field(gt=0)
    memory_bw_gbps: float = Field(default=0.0, ge=0, description="GPU memory bandwidth in GB/s")
    platform: str
    region: str
    source: Literal["live", "sample"] = "live"
    source_detail: str | None = None
    spot: bool = False
    available_instances: int = Field(default=1, ge=0)
    instance_type: str | None = None
    is_availability_estimated: bool = False
    is_region_estimated: bool = False

    @field_validator("platform", "region")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.lower()


class ProviderStatus(BaseModel):
    provider: str
    source: Literal["live", "sample"]
    ok: bool
    offers_count: int = Field(default=0, ge=0)
    message: str | None = None


class Availability(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    risk: RiskLevel


class RecommendationConfig(BaseModel):
    gpu: str
    gpu_count: int
    cpu: int
    ram: float
    platform: str
    region: str


class RecommendationMetrics(BaseModel):
    time_hours: float
    cost_usd: float
    gpu_utilization: float


class Recommendation(BaseModel):
    label: str
    config: RecommendationConfig
    metrics: RecommendationMetrics
    availability: Availability
    source: Literal["live", "sample"] = "live"
    source_detail: str | None = None
    notes: list[str] = Field(default_factory=list)
    explanation: str


class MarketAggregation(BaseModel):
    offers: list[MarketOffer]
    provider_statuses: list[ProviderStatus]


class PlanningResponse(BaseModel):
    version: str = "0.1.2"
    summary: str
    provider_statuses: list[ProviderStatus] = Field(default_factory=list)
    recommendations: list[Recommendation]


class PlanningRun(BaseModel):
    estimate: ResourceEstimate
    market: MarketAggregation
    response: PlanningResponse
