"""Windows OS socket table inspection adapter (TRD ?24.1, ADR-012)."""

import logging
import os
import subprocess
from typing import List, Optional, Set

from backend.app.sovereignty.adapters.base import NetworkInspectionAdapter
from backend.app.sovereignty.events import ConnectionRecord

logger = logging.getLogger("sovereign_workbench.sovereignty.adapter.windows")


class WindowsSocketTableAdapter(NetworkInspectionAdapter):
    """
    Inspects Windows active TCP connection table via least-privileged OS netstat query.
    Filters specifically to the backend process PID and its managed children (TRD ?24.1).
    Zero kernel drivers, zero packet capture, zero privilege elevation required.
    """

    def __init__(self, target_pids: Optional[Set[int]] = None):
        self._target_pids = target_pids

    @property
    def adapter_name(self) -> str:
        return "windows_netstat_adapter"

    @property
    def byte_accounting_supported(self) -> bool:
        # Per TRD ?37 / ADR-012: Windows netstat table provides socket state/IPs but not live byte counters
        return False

    def get_monitored_pids(self) -> Set[int]:
        """Get set of PIDs to inspect (current backend process + any registered children)."""
        pids = {os.getpid()}
        if self._target_pids:
            pids.update(self._target_pids)
        return pids

    def get_active_connections(self) -> List[ConnectionRecord]:
        connections: List[ConnectionRecord] = []
        monitored_pids = self.get_monitored_pids()

        try:
            # Execute netstat -ano -p tcp to get active TCP connections with PIDs
            result = subprocess.run(
                ["netstat", "-ano", "-p", "tcp"],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            if result.returncode != 0:
                logger.warning(f"netstat returned non-zero exit code {result.returncode}")
                return connections

            lines = result.stdout.splitlines()

            for line in lines:
                parts = line.strip().split()
                # Expected format: Proto, Local Address, Foreign Address, State, PID
                if len(parts) >= 5 and parts[0].upper() == "TCP":
                    try:
                        pid = int(parts[4])
                    except ValueError:
                        continue

                    # Filter strictly to the monitored backend process tree (TRD ?24.1)
                    if pid not in monitored_pids:
                        continue

                    local_addr_str = parts[1]
                    remote_addr_str = parts[2]
                    state = parts[3].upper()

                    # Ignore listening ports (only inspect outbound / active connection states)
                    if state == "LISTENING":
                        continue

                    # Parse local address and port
                    local_host, local_port = self._parse_addr_port(local_addr_str)
                    remote_host, remote_port = self._parse_addr_port(remote_addr_str)

                    connections.append(
                        ConnectionRecord(
                            process="backend",
                            pid=pid,
                            local_address=local_host,
                            local_port=local_port,
                            remote_address=remote_host,
                            remote_port=remote_port,
                            state=state,
                            bytes_sent=None,
                            byte_accounting_supported=False,
                        )
                    )
        except Exception as e:
            logger.error(f"Error inspecting Windows socket table: {e}")

        return connections

    @staticmethod
    def _parse_addr_port(addr_str: str) -> tuple[str, Optional[int]]:
        """Parse host:port string handling IPv4 and bracketed IPv6."""
        if not addr_str or addr_str == "*:*" or addr_str == "0.0.0.0:0" or addr_str == "[::]:0":
            return "0.0.0.0", 0

        # Handle IPv6 [::1]:port or IPv4 127.0.0.1:port
        if "]:" in addr_str:
            host_part, port_part = addr_str.rsplit("]:", 1)
            host = host_part.lstrip("[")
            try:
                port = int(port_part)
            except ValueError:
                port = None
            return host, port
        elif ":" in addr_str:
            host, port_str = addr_str.rsplit(":", 1)
            try:
                port = int(port_str)
            except ValueError:
                port = None
            return host, port

        return addr_str, None
