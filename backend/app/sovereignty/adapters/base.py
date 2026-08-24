"""Abstract Base Class for OS-specific Network Inspection Adapters (ADR-012)."""

from abc import ABC, abstractmethod
from typing import List
from backend.app.sovereignty.events import ConnectionRecord


class NetworkInspectionAdapter(ABC):
    """Abstract contract for inspecting operating system socket and process tables."""

    @property
    @abstractmethod
    def adapter_name(self) -> str:
        """Identifier string for this adapter implementation."""
        pass

    @property
    @abstractmethod
    def byte_accounting_supported(self) -> bool:
        """Whether this adapter can reliably measure transmitted socket bytes (TRD ?37)."""
        pass

    @abstractmethod
    def get_active_connections(self) -> List[ConnectionRecord]:
        """Inspect and return the current active outbound network connections."""
        pass
