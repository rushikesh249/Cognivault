"""Deterministic Stub Network Adapter for testing (TRD ?27.1, Implementation Plan Task 9)."""

from typing import List, Optional
from backend.app.sovereignty.adapters.base import NetworkInspectionAdapter
from backend.app.sovereignty.events import ConnectionRecord


class StubNetworkAdapter(NetworkInspectionAdapter):
    """Test adapter providing deterministic connection fixtures."""

    def __init__(
        self,
        connections: Optional[List[ConnectionRecord]] = None,
        byte_accounting: bool = False,
        adapter_name_override: str = "stub_network_adapter",
    ):
        self._connections: List[ConnectionRecord] = connections or []
        self._byte_accounting = byte_accounting
        self._adapter_name = adapter_name_override

    @property
    def adapter_name(self) -> str:
        return self._adapter_name

    @property
    def byte_accounting_supported(self) -> bool:
        return self._byte_accounting

    def set_connections(self, connections: List[ConnectionRecord]) -> None:
        self._connections = connections

    def add_connection(self, conn: ConnectionRecord) -> None:
        self._connections.append(conn)

    def clear(self) -> None:
        self._connections = []

    def get_active_connections(self) -> List[ConnectionRecord]:
        return list(self._connections)
