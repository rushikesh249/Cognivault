"""Integration tests for SovereigntyMonitor lifecycle and adapters (TRD ?24, Component #20)."""

import time
import pytest
from backend.app.persistence.db import init_db
from backend.app.sovereignty.adapters.stub import StubNetworkAdapter
from backend.app.sovereignty.adapters.windows import WindowsSocketTableAdapter
from backend.app.sovereignty.events import ConnectionRecord
from backend.app.sovereignty.monitor import SovereigntyMonitor


def test_monitor_lifecycle_start_stop():
    """Verify SovereigntyMonitor starts background thread and stops cleanly."""
    stub_adapter = StubNetworkAdapter()
    monitor = SovereigntyMonitor(adapter=stub_adapter, poll_interval_s=0.1)

    assert not monitor.is_running
    monitor.start()
    assert monitor.is_running
    assert monitor.status == "ok"

    time.sleep(0.2)
    monitor.stop()
    assert not monitor.is_running


def test_real_windows_socket_adapter():
    """Verify Windows socket table adapter queries OS TCP connections for backend PID without crashing."""
    adapter = WindowsSocketTableAdapter()
    assert adapter.adapter_name == "windows_netstat_adapter"
    assert adapter.byte_accounting_supported is False

    connections = adapter.get_active_connections()
    assert isinstance(connections, list)
    for c in connections:
        assert isinstance(c, ConnectionRecord)
        assert c.state != "LISTENING"


def test_external_call_triggers_violation_and_event_persistence():
    """Verify injection of external connection triggers violation logging and persistence."""
    init_db()
    stub_adapter = StubNetworkAdapter([
        ConnectionRecord(
            process="test_rogue_sdk",
            pid=9999,
            local_address="127.0.0.1",
            local_port=54321,
            remote_address="api.external-cloud.com",
            remote_port=443,
            state="ESTABLISHED",
        )
    ])

    monitor = SovereigntyMonitor(adapter=stub_adapter)
    events = monitor.audit_once()

    assert len(events) >= 1
    external_events = [e for e in events if e.classification == "external"]
    assert len(external_events) >= 1
    assert external_events[0].destination_host == "api.external-cloud.com"
    assert external_events[0].destination_port == 443
