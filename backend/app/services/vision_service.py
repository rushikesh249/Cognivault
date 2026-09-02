"""Vision application orchestration service (TRD ?8.1, Component #13)."""

import logging
from pathlib import Path
from typing import Callable, Optional
from backend.app.core.config import settings
from backend.app.models.exceptions import ModelUnavailable, ProviderUnavailable
from backend.app.models.model_registry import ModelRegistry
from backend.app.models.router import ModelRouter
from backend.app.multimodal.vision_service import (
    VisionInvalidImageError,
    VisionModelUnavailableError,
    VisionOutputValidationError,
    VisionResult,
    VisionService,
    VisionTimeoutError,
    get_vision_service,
)
from backend.app.persistence.db import get_db_context
from backend.app.persistence.file_repository import FileRepository

logger = logging.getLogger("sovereign_workbench.services.vision")

SUPPORTED_IMAGE_MIMES = {"image/jpeg", "image/png"}


class VisionAppServiceError(Exception):
    """Base application exception for vision orchestration."""
    pass


class VisionFileNotFoundError(VisionAppServiceError):
    """Raised when file_id or storage path cannot be resolved."""
    pass


class VisionUnsupportedFileTypeError(VisionAppServiceError):
    """Raised when uploaded file is not a supported image."""
    pass


class VisionAppService:
    """Application service for vision analysis requests."""

    def __init__(self, domain_service: Optional[VisionService] = None):
        self._domain_service = domain_service or get_vision_service()

    def analyze_file(
        self,
        file_id: str,
        prompt: Optional[str] = None,
        on_retry: Optional[Callable[[int, int, str], None]] = None,
    ) -> VisionResult:
        """Resolve file from repository, route model, and execute vision analysis."""
        if not file_id or not file_id.strip():
            raise VisionAppServiceError("File ID must not be empty.")

        clean_file_id = file_id.strip()

        # 1. Resolve file path from FileRepository or disk
        target_path: Optional[Path] = None
        mime_type: Optional[str] = None

        with get_db_context() as session:
            repo = FileRepository(session)
            file_rec = repo.get_by_id(clean_file_id)
            if file_rec:
                target_path = Path(file_rec.storage_path)
                mime_type = file_rec.mime_type

        if target_path is None or not target_path.exists():
            # Check uploads and demo_inputs as fallback
            direct_upload = settings.paths.uploads_dir / clean_file_id
            demo_path = Path("knowledge_base/demo_inputs") / clean_file_id
            if direct_upload.exists():
                target_path = direct_upload
            elif demo_path.exists():
                target_path = demo_path
            else:
                # Check for standard extension match in uploads
                for ext in [".jpg", ".jpeg", ".png"]:
                    cand = settings.paths.uploads_dir / f"{clean_file_id}{ext}"
                    if cand.exists():
                        target_path = cand
                        break

        if target_path is None or not target_path.exists():
            raise VisionFileNotFoundError(f"Target image file '{clean_file_id}' not found.")

        # 2. Validate MIME type
        if mime_type and mime_type not in SUPPORTED_IMAGE_MIMES:
            raise VisionUnsupportedFileTypeError(
                f"File '{clean_file_id}' has unsupported MIME type '{mime_type}'. "
                f"Allowed image types: {SUPPORTED_IMAGE_MIMES}"
            )
        elif not mime_type:
            suffix = target_path.suffix.lower()
            if suffix not in [".jpg", ".jpeg", ".png"]:
                raise VisionUnsupportedFileTypeError(
                    f"File '{target_path.name}' is not a supported image format. "
                    f"Expected .jpg, .jpeg, or .png."
                )

        # 3. Model routing via declarative ModelRouter (TRD Section 14, Section 14.1)
        registry = ModelRegistry()
        try:
            selected_model_id = ModelRouter.select_for_task_type(
                task_type="vision",
                registry=registry,
                provider=self._domain_service._provider,
                enforce_availability=False,  # Let provider attempt load/generate
            )
        except Exception as e:
            logger.warning(f"ModelRouter failed to select vision model: {e}")
            selected_model_id = "local-vision-model"

        model_cfg = registry.get(selected_model_id)
        model_path = model_cfg.model_path if model_cfg else selected_model_id

        # 4. Invoke domain vision service
        try:
            return self._domain_service.analyze(
                image_path=target_path,
                prompt=prompt,
                model_id=selected_model_id,
                model_path=model_path,
                on_retry=on_retry,
            )
        except VisionTimeoutError as e:
            logger.error(f"Vision model timed out: {e}")
            raise
        except (VisionModelUnavailableError, ModelUnavailable, ProviderUnavailable) as e:
            logger.error(f"Vision model unavailable: {e}")
            raise VisionModelUnavailableError(str(e)) from e
        except VisionInvalidImageError as e:
            raise VisionAppServiceError(str(e)) from e
        except VisionOutputValidationError as e:
            raise VisionAppServiceError(f"Vision output validation failed: {e}") from e


_app_service_instance: Optional[VisionAppService] = None


def get_vision_app_service() -> VisionAppService:
    global _app_service_instance
    if _app_service_instance is None:
        _app_service_instance = VisionAppService()
    return _app_service_instance


def set_vision_app_service(service: VisionAppService) -> None:
    global _app_service_instance
    _app_service_instance = service
