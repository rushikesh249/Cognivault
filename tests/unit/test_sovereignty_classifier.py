"""Unit tests for Sovereignty connection classifier and events schema (TRD ?24.1, ADR-012)."""

import datetime
import pytest
from backend.app.sovereignty.adapters.stub import StubNetworkAdapter
from backend.app.sovereignty.events import ConnectionRecord, SovereigntyEvent, SovereigntyStatus
from backend.app.sovereignty.monitor import SovereigntyMonitor


def test_local_allowlist_classification():
    """Verify localhost, 127.0.0.1, ::1, and allowed ports classify strictly as 'local'."""
    monitor = SovereigntyMonitor(
        adapter=StubNetworkAdapter(),
        allowlist_hosts={"127.0.0.1", "localhost", "::1", "0.0.0.0"},
        allowlist_ports={11434, 8000, 5173},
    )

    local_conns = [
        ConnectionRecord(remote_address="127.0.0.1", remote_port=11434, state="ESTABLISHED"),
        ConnectionRecord(remote_address="localhost", remote_port=8000, state="ESTABLISHED"),
        ConnectionRecord(remote_address="::1", remote_port=5173, state="ESTABLISHED"),
        ConnectionRecord(remote_address="0.0.0.0", remote_port=0, state="NONE"),
        ConnectionRecord(remote_address="127.0.0.1", remote_port=49152, state="ESTABLISHED"),
    ]

    for conn in local_conns:
        assert monitor.classify_connection(conn) == "local"


def test_external_destination_classification():
    """Verify any non-allowlisted destination classifies as 'external' (TRD ?24.1)."""
    monitor = SovereigntyMonitor(
        adapter=StubNetworkAdapter(),
        allowlist_hosts={"127.0.0.1", "localhost", "::1", "0.0.0.0"},
        allowlist_ports={11434, 8000, 5173},
    )

    external_conns = [
        ConnectionRecord(remote_address="api.openai.com", remote_port=443, state="ESTABLISHED"),
        ConnectionRecord(remote_address="142.250.190.46", remote_port=443, state="ESTABLISHED"),
        ConnectionRecord(remote_address="54.239.28.85", remote_port=80, state="ESTABLISHED"),
        ConnectionRecord(remote_address="192.168.1.50", remote_port=9000, state="ESTABLISHED"),
    ]

    for conn in external_conns:
        assert monitor.classify_connection(conn) == "external"


def test_blocked_connection_classification():
    """Verify refused / blocked connection states classify as 'blocked'."""
    monitor = SovereigntyMonitor(adapter=StubNetworkAdapter())

    blocked_conns = [
        ConnectionRecord(remote_address="10.0.0.5", remote_port=443, state="BLOCKED"),
        ConnectionRecord(remote_address="api.anthropic.com", remote_port=443, state="REFUSED"),
        ConnectionRecord(remote_address="example.com", remote_port=80, state="SYN_SENT_TIMEOUT"),
    ]

    for conn in blocked_conns:
        assert monitor.classify_connection(conn) == "blocked"


def test_sovereignty_event_and_status_schema():
    """Verify Pydantic models serialize and validate matching TRD Table 20 and Table 52."""
    now = datetime.datetime.now(datetime.timezone.utc)
    ev = SovereigntyEvent(
        event_id="test-ev-01",
        ts=now,
        process="backend",
        destination_host="127.0.0.1",
        destination_port=11434,
        classification="local",
        bytes_sent=1024,
        byte_accounting_supported=False,
        dns_observed=False,
        adapter="stub_adapter",
    )
    assert ev.classification == "local"
    assert ev.destination_port == 11434

    status = SovereigntyStatus(
        external_ai_calls=0,
        external_embedding_calls=0,
        external_ocr_calls=0,
        data_egress_mb=0.0,
        local_inference="ok",
        local_ocr="ok",
        local_rag="ok",
        local_vision="ok",
        local_sandbox="ok",
        monitor_status="ok",
        byte_accounting_supported=False,
        external_connections_5m=0,
        external_dns_lookups_5m=0,
    )
    # Verify all 10 required TRD fields
    assert status.external_ai_calls == 0
    assert status.external_embedding_calls == 0
    assert status.external_ocr_calls == 0
    assert status.data_egress_mb == 0.0
    assert status.local_inference == "ok"
    assert status.local_ocr == "ok"
    assert status.local_rag == "ok"
    assert status.local_vision == "ok"
    assert status.local_sandbox == "ok"
    assert status.monitor_status == "ok"
    # Verify supplementary fields
    assert status.byte_accounting_supported is False
    assert status.external_connections_5m == 0
    assert status.external_dns_lookups_5m == 0
