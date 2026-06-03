from __future__ import annotations

from fastapi import APIRouter

from backend.app.schemas.sample_analysis import CapabilityResponse, HealthResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@router.get("/capabilities", response_model=CapabilityResponse)
def capabilities() -> CapabilityResponse:
    return CapabilityResponse(
        capabilities=[
            "sample-analysis",
            "analysis-intent-routing",
            "analysis-view-model",
            "transfer",
            "asset-gap-detection",
            "edit-iterate",
        ],
        providers=[
            "heuristic-local",
            "ark-chat-completions",
        ],
        strategies=[
            "script-structure-extraction",
            "pace-structure-extraction",
            "intent-routing",
            "asset-gap-fill-planned",
        ],
    )
