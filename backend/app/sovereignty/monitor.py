"""Sovereignty Monitor domain implementation (TRD ?24, Component #20, ADR-012)."""

import datetime
import logging
import platform
import threading
import time
from typing import Dict, List, Optional, Set, Tuple

from backend.app.core.config import settings
from backend.app.persistence.db import get_db_context
from backend.app.persistence.sovereignty_repository import SovereigntyRepository
from backend.app.sovereignty.adapters.base import NetworkInspectionAdapter
from backend.app.sovereignty.adapters.linux import LinuxProcNetAdapter
from backend.app.sovereignty.adapters.windows import WindowsSocketTableAdapter
from backend.app.sovereignty.events import ConnectionRecord, SovereigntyEvent, SovereigntyStatus

logger = logging.getLogger("sovereign_workbench.sovereignty.monitor")

DEFAULT_LOCAL_HOSTS: Set[str] = {"127.0.0.1", "localhost", "::1", "0.0.0.0", "::"}
DEFAULT_LOCAL_PORTS: Set[int] = {11434, 8000, 5173}


def get_default_os_adapter() -> NetworkInspectionAdapter:
    """Factory to select least-privileged OS adapter based on platform."""
    system = platform.system().lower()
    if "windows" in system:
        return WindowsSocketTableAdapter()
    elif "linux" in system:
        return LinuxProcNetAdapter()
    return WindowsSocketTableAdapter()


class SovereigntyMonitor:
    """
    Continuous runtime process and network monitor ensuring zero cloud egress (TRD ?24).
    """

    def __init__(
        self,
        adapter: Optional[NetworkInspectionAdapter] = None,
        poll_interval_s: Optional[float] = None,
        allowlist_hosts: Optional[Set[str]] = None,
        allowlist_ports: Optional[Set[int]] = None,
    ):
        self.adapter = adapter or get_default_os_adapter()
        self.poll_interval_s = (
            poll_interval_s
            if poll_interval_s is not None
            else getattr(settings.sovereignty, "poll_interval_s", 1.0)
        )

        cfg_hosts = set(getattr(settings.sovereignty, "allowlist_hosts", []))
        self.allowlist_hosts = (allowlist_hosts or DEFAULT_LOCAL_HOSTS) | cfg_hosts

        cfg_ports = set(getattr(settings.sovereignty, "allowlist_ports", []))
        self.allowlist_ports = (allowlist_ports or DEFAULT_LOCAL_PORTS) | cfg_ports

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        self._last_audit_ts: Optional[datetime.datetime] = None
        self._status: str = "ok"  # 'ok' or 'degraded'
        self._last_error: Optional[str] = None

        # Deduplication cache: (remote_host, remote_port, classification) -> last_logged_timestamp
        self._seen_connections: Dict[Tuple[str, Optional[int], str], float] = {}

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def status(self) -> str:
        return self._status

    def classify_connection(self, conn: ConnectionRecord) -> str:
        """
        Classify connection into 'local', 'external', or 'blocked' (TRD ?24.1).
        """
        remote_host = (conn.remote_address or "").strip().lower()
        remote_port = conn.remote_port
        state = (conn.state or "").upper()

        # Connections actively rejected or refused
        if state in ("BLOCKED", "REFUSED", "SYN_SENT_TIMEOUT"):
            return "blocked"

        # Check loopback and empty destinations
        if not remote_host or remote_host == "0.0.0.0" or remote_host == "*":
            return "local"

        is_local_host = (
            remote_host in self.allowlist_hosts
            or remote_host.startswith("127.")
            or remote_host == "localhost"
        )

        # If host is loopback, verify port is within allowed local application ports (or zero/null)
        if is_local_host:
            if remote_port is None or remote_port == 0 or remote_port in self.allowlist_ports or remote_port > 1024:
                return "local"

        # Any non-allowlisted destination is strictly external
        return "external"

    def audit_once(self) -> List[SovereigntyEvent]:
        """Perform a single socket table audit sweep and persist any events."""
        events_recorded: List[SovereigntyEvent] = []
        try:
            active_conns = self.adapter.get_active_connections()
            now = datetime.datetime.now(datetime.timezone.utc)
            now_epoch = time.time()

            with get_db_context() as session:
                repo = SovereigntyRepository(session)

                for conn in active_conns:
                    classification = self.classify_connection(conn)
                    remote_host = conn.remote_address or "0.0.0.0"
                    remote_port = conn.remote_port
                    dedup_key = (remote_host, remote_port, classification)

                    # Deduplicate: only record same remote connection once every 30 seconds
                    last_seen = self._seen_connections.get(dedup_key, 0.0)
                    if (now_epoch - last_seen) < 30.0:
                        continue

                    self._seen_connections[dedup_key] = now_epoch

                    # Persist event to database
                    orm_event = repo.create(
                        process=conn.process,
                        destination_host=remote_host,
                        destination_port=remote_port,
                        classification=classification,
                        bytes_sent=conn.bytes_sent,
                        byte_accounting_supported=self.adapter.byte_accounting_supported,
                        dns_observed=False,
                        adapter=self.adapter.adapter_name,
                        ts=now,
                    )

                    event_model = SovereigntyEvent(
                        event_id=orm_event.event_id,
                        ts=orm_event.ts,
                        process=orm_event.process,
                        destination_host=orm_event.destination_host,
                        destination_port=orm_event.destination_port,
                        classification=orm_event.classification,
                        bytes_sent=orm_event.bytes_sent,
                        byte_accounting_supported=orm_event.byte_accounting_supported,
                        dns_observed=orm_event.dns_observed,
                        adapter=orm_event.adapter,
                    )
                    events_recorded.append(event_model)

                    if classification == "external":
                        logger.critical(
                            f"SOVEREIGNTY VIOLATION DETECTED: External connection to {remote_host}:{remote_port} "
                            f"from process {conn.process} (PID: {conn.pid})"
                        )

            with self._lock:
                self._last_audit_ts = now
                self._status = "ok"
                self._last_error = None

        except Exception as e:
            logger.error(f"SovereigntyMonitor audit failed: {e}")
            with self._lock:
                self._status = "degraded"
                self._last_error = str(e)

        return events_recorded

    def _run_loop(self) -> None:
        """Background loop running at poll_interval_s."""
        logger.info(f"SovereigntyMonitor background thread started (adapter: {self.adapter.adapter_name}, interval: {self.poll_interval_s}s)")
        while not self._stop_event.is_set():
            self.audit_once()
            self._stop_event.wait(self.poll_interval_s)
        logger.info("SovereigntyMonitor background thread terminated cleanly")

    def start(self) -> None:
        """Start background monitor thread."""
        with self._lock:
            if self._running:
                return
            self._stop_event.clear()
            self._running = True
            self._thread = threading.Thread(
                target=self._run_loop,
                name="SovereigntyMonitorWorker",
                daemon=True,
            )
            self._thread.start()

    def stop(self, timeout_s: float = 2.0) -> None:
        """Stop background monitor thread."""
        with self._lock:
            if not self._running:
                return
            self._stop_event.set()
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=timeout_s)
            self._running = False


# Global singleton instance
_monitor_instance: Optional[SovereigntyMonitor] = None


def get_sovereignty_monitor() -> SovereigntyMonitor:
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = SovereigntyMonitor()
    return _monitor_instance


def set_sovereignty_monitor(monitor: SovereigntyMonitor) -> None:
    global _monitor_instance
    _monitor_instance = monitor
