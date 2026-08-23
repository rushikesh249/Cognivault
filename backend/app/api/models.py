"""Model Registry and probe API endpoints (TRD §9, §13, Table 19)."""

from fastapi import APIRouter, Depends
from backend.app.core.config import settings
from backend.app.models.model_registry import ModelRegistry
from backend.app.models.ollama_adapter import OllamaAdapter
from backend.app.models.schema import ModelInfoOut, ModelListOut

router = APIRouter(prefix="/api", tags=["Models"])

# Module-level instances for request dependency injection
_registry = ModelRegistry()
_adapter = OllamaAdapter(
    base_url=settings.ollama.base_url,
    timeout_s=settings.ollama.timeout_s,
    cache_ttl_s=settings.ollama.cache_ttl_s,
)


def get_model_registry() -> ModelRegistry:
    return _registry


def get_model_adapter() -> OllamaAdapter:
    return _adapter


@router.get("/models", response_model=ModelListOut)
async def list_models(
    registry: ModelRegistry = Depends(get_model_registry),
    adapter: OllamaAdapter = Depends(get_model_adapter),
) -> ModelListOut:
    """
    GET /api/models (TRD §9, Table 19)
    Returns configured Model Registry entries with live local provider availability probe.
    """
    models_out = []
    provider_status = adapter.get_provider_status()

    for model in registry.list():
        is_available = adapter.is_model_available(model.model_path) if model.enabled else False
        model_status = adapter.get_model_status(model)

        models_out.append(
            ModelInfoOut(
                model_id=model.model_id,
                display_name=model.display_name,
                role=model.role,
                capabilities=model.capabilities,
                modalities=model.modalities,
                context_length=model.context_length,
                vram_gb=model.vram_gb,
                serving_backend=model.serving_backend,
                model_path=model.model_path,
                enabled=model.enabled,
                available=is_available,
                status=model_status,
                provider_status=provider_status,
            )
        )

    return ModelListOut(models=models_out)
