"""Vision API Router (TRD ?9, Table 16)."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.app.multimodal.vision_service import VisionModelUnavailableError, VisionResult
from backend.app.services.vision_service import (
    VisionAppService,
    VisionFileNotFoundError,
    VisionUnsupportedFileTypeError,
    get_vision_app_service,
)

logger = logging.getLogger("sovereign_workbench.api.vision")

router = APIRouter(prefix="/api/vision", tags=["Vision"])


class VisionRequest(BaseModel):
    """Request schema for vision analysis (TRD Table 16)."""
    file_id: str = Field(..., min_length=1, description="Uploaded image file identifier")
    prompt: Optional[str] = Field(None, description="Optional custom inspection instructions")


@router.post(
    "/analyze",
    response_model=VisionResult,
    status_code=status.HTTP_200_OK,
    summary="Run local VLM over an uploaded image (TRD Table 16)",
)
async def analyze_image_endpoint(
    request: VisionRequest,
    service: VisionAppService = Depends(get_vision_app_service),
) -> VisionResult:
    """
    POST /api/vision/analyze (TRD Table 16)
    Runs local VLM over an uploaded image and returns structured findings:
    - 200 OK: Returns VisionResult { observation, interpretation, uncertainty, model_used }
    - 400 Bad Request: Non-image or unsupported file format.
    - 404 Not Found: file_id missing from registry or storage.
    - 422 Unprocessable Entity: Empty or invalid file_id.
    - 503 Service Unavailable: Local vision model or Ollama server unavailable.
    """
    try:
        return service.analyze_file(file_id=request.file_id, prompt=request.prompt)
    except VisionFileNotFoundError as e:
        logger.warning(f"Vision file not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except VisionUnsupportedFileTypeError as e:
        logger.warning(f"Unsupported vision file: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except VisionModelUnavailableError as e:
        logger.error(f"Vision model unavailable: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Local vision model is unavailable: {e}",
        )
    except Exception as e:
        logger.error(f"Vision analysis error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vision analysis failed: {e}",
        )
