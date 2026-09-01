"""Sovereignty Application Service (TRD ?8.1 Table 8, ?24.3 Component #20)."""

import logging
from typing import Optional
from backend.app.models.model_registry import ModelRegistry
from backend.app.models.ollama_adapter import OllamaAdapter
from backend.app.persistence.db import get_db_context
from backend.app.persistence.sovereignty_repository import SovereigntyRepository
from backend.app.sandbox.docker_runner import DockerRunner
from backend.app.sovereignty.events import SovereigntyStatus
from backend.app.sovereignty.monitor import SovereigntyMonitor, get_sovereignty_monitor

logger = logging.getLogger("sovereign_workbench.services.sovereignty")


class SovereigntyAppService:
    """Service providing live sovereignty status and subsystem health checks."""

    def __init__(self, monitor: Optional[SovereigntyMonitor] = None):
        self._monitor = monitor or get_sovereignty_monitor()
        self._ollama_adapter = OllamaAdapter()
        self._docker_runner = DockerRunner()

    def get_status(self, window_minutes: int = 5) -> SovereigntyStatus:
        """
        Aggregate live sovereignty counters and evaluate subsystem health flags (TRD Table 20).
        """
        # 1. Trigger single audit sweep to ensure freshest data
        try:
            self._monitor.audit_once()
        except Exception as e:
            logger.warning(f"Error during on-demand sovereignty sweep: {e}")

        # 2. Query aggregated counters from repository
        with get_db_context() as session:
            repo = SovereigntyRepository(session)
            stats = repo.get_aggregated_stats(window_minutes=window_minutes)

        external_ai = stats.get("external_ai_calls", 0)
        external_embedding = stats.get("external_embedding_calls", 0)
        external_ocr = stats.get("external_ocr_calls", 0)
        data_egress_mb = stats.get("data_egress_mb", 0.0)

        # 3. Check subsystem health flags
        # local_inference
        local_inference_status = "ok"
        try:
            if not self._ollama_adapter.is_provider_available():
                local_inference_status = "degraded"
        except Exception:
            local_inference_status = "degraded"

        # local_ocr
        local_ocr_status = "ok"

        # local_rag
        local_rag_status = "ok"

        # local_vision
        local_vision_status = "ok"
        try:
            registry = ModelRegistry()
            vlm_cfg = registry.get("local-vision-model")
            if not vlm_cfg or not vlm_cfg.enabled:
                local_vision_status = "degraded"
        except Exception:
            local_vision_status = "degraded"

        # local_sandbox
        local_sandbox_status = "ok"
        try:
            if not self._docker_runner.is_available():
                local_sandbox_status = "degraded"
        except Exception:
            local_sandbox_status = "degraded"

        # monitor_status
        monitor_status = self._monitor.status
        if stats.get("external_count", 0) > 0:
            # Violation detected: monitor flag becomes degraded / violation alert
            monitor_status = "degraded"

        return SovereigntyStatus(
            # Required TRD Table 20 fields
            external_ai_calls=external_ai,
            external_embedding_calls=external_embedding,
            external_ocr_calls=external_ocr,
            data_egress_mb=data_egress_mb,
            local_inference=local_inference_status,
            local_ocr=local_ocr_status,
            local_rag=local_rag_status,
            local_vision=local_vision_status,
            local_sandbox=local_sandbox_status,
            monitor_status=monitor_status,
            # Supplementary monitoring fields (ADR-012)
            byte_accounting_supported=stats.get("byte_accounting_supported", False),
            external_connections_5m=stats.get("external_count", 0),
            external_dns_lookups_5m=0,  # DNS lookup tracking not yet implemented
        )


_sovereignty_app_service_instance: Optional[SovereigntyAppService] = None


def get_sovereignty_app_service() -> SovereigntyAppService:
    global _sovereignty_app_service_instance
    if _sovereignty_app_service_instance is None:
        _sovereignty_app_service_instance = SovereigntyAppService()
    return _sovereignty_app_service_instance


def set_sovereignty_app_service(service: SovereigntyAppService) -> None:
    global _sovereignty_app_service_instance
    _sovereignty_app_service_instance = service
