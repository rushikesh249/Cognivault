"""Capability-based Model Router (TRD §14, §15, ADR-004, ADR-014)."""

import logging
from typing import List, Optional

from backend.app.core.config import RoutingSettings, settings
from backend.app.models.exceptions import ModelUnavailable
from backend.app.models.model_registry import ModelRegistry
from backend.app.models.provider import ModelProvider
from backend.app.models.schema import ModelConfig, TaskRequirement

logger = logging.getLogger("sovereign_workbench.models.router")


class ModelRouter:
    """
    Deterministic, capability-matching model router with hardware fallback support.
    Routing decisions are configuration-driven, not hardcoded if/else code branches (TRD §14.1).
    """

    @classmethod
    def get_requirement_for_task_type(
        cls,
        task_type: str,
        routing_settings: Optional[RoutingSettings] = None,
    ) -> TaskRequirement:
        """
        Resolve TaskRequirement from declarative configuration (TRD §14.1, Table 34).
        Adding a new task type is a configuration change, not a code branch.
        """
        cfg = routing_settings or settings.routing
        if task_type not in cfg.task_requirements:
            valid_types = list(cfg.task_requirements.keys())
            raise ValueError(
                f"Unknown task_type '{task_type}' in declarative routing configuration. "
                f"Configured task types: {valid_types}"
            )

        req_config = cfg.task_requirements[task_type]
        return TaskRequirement(
            task_type=task_type,
            preferred_role=req_config.preferred_role,
            modality=req_config.modality,
            capabilities=list(req_config.capabilities),
        )

    @classmethod
    def select_for_task_type(
        cls,
        task_type: str,
        registry: ModelRegistry,
        provider: Optional[ModelProvider] = None,
        enforce_availability: bool = True,
        routing_settings: Optional[RoutingSettings] = None,
    ) -> str:
        """
        Convenience method to resolve declarative requirement and select model_id (TRD §14).
        """
        requirement = cls.get_requirement_for_task_type(task_type, routing_settings=routing_settings)
        return cls.select(
            requirement=requirement,
            registry=registry,
            provider=provider,
            enforce_availability=enforce_availability,
        )

    @classmethod
    def select(
        cls,
        requirement: TaskRequirement,
        registry: ModelRegistry,
        provider: Optional[ModelProvider] = None,
        enforce_availability: bool = True,
    ) -> str:
        """
        Select best model_id matching TaskRequirement per TRD §14 pseudocode:
        1. Filter enabled candidates matching modality and capabilities subset.
        2. Filter by hardware constraints (max_vram_gb, max_context_needed).
        3. Filter by provider availability if provider given and enforce_availability=True.
        4. Sort deterministically: exact preferred_role match first, then narrowest context_length.
        5. If empty, invoke fallback_chain().
        """
        req_capabilities = set(requirement.capabilities)

        # 1. Capability & Modality Filter
        candidates: List[ModelConfig] = [
            m for m in registry.list(enabled_only=True)
            if requirement.modality in m.modalities
            and req_capabilities.issubset(set(m.capabilities))
        ]

        # 2. Hardware constraints filter
        if requirement.max_vram_gb is not None:
            candidates = [
                m for m in candidates
                if m.vram_gb is None or m.vram_gb <= requirement.max_vram_gb
            ]

        if requirement.max_context_needed is not None:
            candidates = [
                m for m in candidates
                if m.context_length >= requirement.max_context_needed
            ]

        # 3. Local provider availability filter
        if provider is not None and enforce_availability:
            candidates = [
                m for m in candidates
                if provider.is_model_available(m.model_path or m.model_id)
            ]

        # 4. Fallback chain if no candidates match
        if not candidates:
            return cls.fallback_chain(
                requirement=requirement,
                registry=registry,
                provider=provider,
                enforce_availability=enforce_availability,
            )

        # 5. Deterministic scoring: exact role match first, then narrowest suitable context_length
        candidates.sort(
            key=lambda m: (
                m.role != requirement.preferred_role if requirement.preferred_role else False,
                m.context_length,
            )
        )

        selected = candidates[0]
        logger.info(
            f"Selected model '{selected.model_id}' (role={selected.role}) for requirement: "
            f"role={requirement.preferred_role}, modality={requirement.modality}, capabilities={requirement.capabilities}"
        )
        return selected.model_id

    @classmethod
    def fallback_chain(
        cls,
        requirement: TaskRequirement,
        registry: ModelRegistry,
        provider: Optional[ModelProvider] = None,
        enforce_availability: bool = True,
    ) -> str:
        """
        Hardware-aware fallback chain (TRD §15.2, ADR-014):
        1. Look for any enabled model covering modality and capabilities regardless of role.
        2. Fallback to general-purpose model if its capabilities cover the requirement.
        3. If still no candidates, raise ModelUnavailable (NEVER fall back to cloud).
        """
        logger.warning(f"Initiating fallback chain for requirement: {requirement}")
        req_capabilities = set(requirement.capabilities)

        # Step 1: Any enabled model covering modality and capabilities regardless of preferred role
        fallback_candidates = [
            m for m in registry.list(enabled_only=True)
            if requirement.modality in m.modalities
            and req_capabilities.issubset(set(m.capabilities))
        ]

        if provider is not None and enforce_availability:
            fallback_candidates = [
                m for m in fallback_candidates
                if provider.is_model_available(m.model_path or m.model_id)
            ]

        if fallback_candidates:
            # Sort by context length
            fallback_candidates.sort(key=lambda m: m.context_length)
            selected = fallback_candidates[0]
            logger.info(f"Fallback matched candidate: {selected.model_id}")
            return selected.model_id

        # Step 2: If no explicit custom capabilities were demanded, general-purpose models can serve as fallback
        if not req_capabilities:
            general_models = [
                m for m in registry.get_by_role("general", enabled_only=True)
                if requirement.modality in m.modalities
            ]
            if provider is not None and enforce_availability:
                general_models = [
                    m for m in general_models
                    if provider.is_model_available(m.model_path or m.model_id)
                ]

            if general_models:
                general_models.sort(key=lambda m: m.context_length)
                selected = general_models[0]
                logger.info(f"Single-model general fallback matched: {selected.model_id}")
                return selected.model_id

        # Step 3: No candidates available -> explicit failure (NEVER fallback to cloud!)
        raise ModelUnavailable(
            f"No suitable local model available for task requirement: "
            f"role='{requirement.preferred_role}', modality='{requirement.modality}', capabilities={requirement.capabilities}"
        )
