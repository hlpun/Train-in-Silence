from __future__ import annotations

from fastapi import Body, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from tis.planner.models import Constraints, PlanningRequest, PlanningResponse, ProviderStatus
from tis.planner.recommender import PlannerService

APP_VERSION = "0.1.3"


class APIError(BaseModel):
    code: str
    message: str
    details: list[dict] | None = None


class APIErrorResponse(BaseModel):
    error: APIError
    version: str = APP_VERSION


class HealthResponse(BaseModel):
    status: str
    version: str


class ProvidersResponse(BaseModel):
    version: str = APP_VERSION
    providers: list[ProviderStatus]


app = FastAPI(
    title="Train in Silence",
    version=APP_VERSION,
    description=(
        "LLM fine-tuning hardware planner MVP. "
        "This service is a planning aid, not a guaranteed pricing or training-performance oracle."
    ),
)
service = PlannerService()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Sanitize errors to ensure they are JSON serializable (Pydantic V2 can include raw exceptions in ctx)
    errors = []
    for error in exc.errors():
        if "ctx" in error:
            error["ctx"] = {k: str(v) for k, v in error["ctx"].items()}
        errors.append(error)

    return JSONResponse(
        status_code=422,
        content=APIErrorResponse(
            error=APIError(code="validation_error", message="Request validation failed.", details=errors)
        ).model_dump(mode="json"),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=APIErrorResponse(
            error=APIError(code="internal_error", message=str(exc), details=None)
        ).model_dump(mode="json"),
    )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", version=APP_VERSION)


@app.get("/version")
def version() -> dict[str, str]:
    return {"version": APP_VERSION}


@app.get("/providers", response_model=ProvidersResponse)
def providers() -> ProvidersResponse:
    market = service.market.fetch_market_data(Constraints())
    return ProvidersResponse(providers=market.provider_statuses)


@app.post(
    "/recommend",
    response_model=PlanningResponse,
    responses={
        422: {"model": APIErrorResponse, "description": "Validation error"},
        500: {"model": APIErrorResponse, "description": "Internal error"},
    },
)
def recommend(
    request: PlanningRequest = Body(
        ...,
        openapi_examples={
            "basic": {
                "summary": "QLoRA on llama-13b",
                "value": {
                    "workload": {
                        "model": {
                            "name": "llama-13b", 
                            "params": 13000000000, 
                            "architecture": "decoder-only",
                            "hidden_dim": 5120,
                            "num_layers": 40,
                            "num_heads": 40,
                            "num_kv_heads": 40
                        },
                        "training": {
                            "method": "qlora",
                            "precision": "bf16",
                            "batch_size": 4,
                            "grad_accum": 8,
                            "seq_len": 2048,
                            "epochs": 3,
                        },
                        "data": {"dataset_tokens": 100000000},
                    },
                    "constraints": {
                        "platforms": ["vast.ai", "runpod", "aws"],
                        "max_budget": 20,
                        "max_time_hours": 12,
                        "region": ["us", "eu"],
                        "max_gpus": 4,
                    },
                    "preference": {"optimize_for": "balanced"},
                },
            }
        },
    ),
) -> PlanningResponse:
    return service.recommend(request)
