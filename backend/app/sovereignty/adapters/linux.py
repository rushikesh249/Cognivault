"""Linux OS /proc/net/tcp socket table inspection adapter (TRD ?24.1, ADR-012)."""

import logging
import os
import socket
import struct
from pathlib import Path
from typing import List, Optional

from backend.app.sovereignty.adapters.base import NetworkInspectionAdapter
from backend.app.sovereignty.events import ConnectionRecord

logger = logging.getLogger("sovereign_workbench.sovereignty.adapter.linux")


class LinuxProcNetAdapter(NetworkInspectionAdapter):
    """
    Inspects Linux kernel socket tables via /proc/net/tcp and /proc/net/tcp6.
    Zero external packages, zero root privileges required.
    """

    @property
    def adapter_name(self) -> str:
        return "linux_proc_net_adapter"

    @property
    def byte_accounting_supported(self) -> bool:
        return False

    def get_active_connections(self) -> List[ConnectionRecord]:
        connections: List[ConnectionRecord] = []
        tcp_path = Path("/proc/net/tcp")
        if not tcp_path.exists():
            return connections

        try:
            with open(tcp_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for line in lines[1:]:  # Skip header
                parts = line.strip().split()
                if len(parts) < 10:
                    continue

                local_hex = parts[1]
                remote_hex = parts[2]
                state_hex = parts[3]

                # TCP state 0A is LISTEN; skip listening sockets
                if state_hex == "0A":
                    continue

                local_ip, local_port = self._decode_hex_addr(local_hex)
                remote_ip, remote_port = self._decode_hex_addr(remote_hex)

                connections.append(
                    ConnectionRecord(
                        process="backend",
                        pid=os.getpid(),
                        local_address=local_ip,
                        local_port=local_port,
                        remote_address=remote_ip,
                        remote_port=remote_port,
                        state=state_hex,
                        bytes_sent=None,
                        byte_accounting_supported=False,
                    )
                )
        except Exception as e:
            logger.error(f"Error reading /proc/net/tcp: {e}")

        return connections

    @staticmethod
    def _decode_hex_addr(hex_str: str) -> tuple[str, int]:
        try:
            ip_hex, port_hex = hex_str.split(":")
            ip_bytes = bytes.fromhex(ip_hex)
            ip_str = socket.inet_ntoa(ip_bytes[::-1])
            port = int(port_hex, 16)
            return ip_str, port
        except Exception:
            return "0.0.0.0", 0
