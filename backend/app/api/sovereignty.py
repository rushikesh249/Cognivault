"""Sovereignty API endpoints (TRD ?9, Table 20)."""

import logging
from fastapi import APIRouter, Depends
from backend.app.services.sovereignty_service import SovereigntyAppService, get_sovereignty_app_service
from backend.app.sovereignty.events import SovereigntyStatus

logger = logging.getLogger("sovereign_workbench.api.sovereignty")

router = APIRouter(prefix="/api/sovereignty", tags=["sovereignty"])


@router.get(
    "/status",
    response_model=SovereigntyStatus,
    summary="Get live sovereignty counters and health status",
    description="Returns live outbound network counters and subsystem health flags (TRD Table 20).",
)
def get_sovereignty_status(
    service: SovereigntyAppService = Depends(get_sovereignty_app_service),
) -> SovereigntyStatus:
    """Return live sovereignty metrics and health states for the Sovereignty Monitor panel."""
    return service.get_status()
