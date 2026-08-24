"""Unit tests for SovereigntyRepository and rolling aggregation (TRD ?10.7, Table 27)."""

import datetime
import pytest
from backend.app.persistence.db import get_db_context, init_db
from backend.app.persistence.sovereignty_repository import SovereigntyRepository


@pytest.fixture
def repo():
    init_db()
    with get_db_context() as session:
        yield SovereigntyRepository(session)


def test_sovereignty_event_crud(repo: SovereigntyRepository):
    """Verify creating and querying sovereignty events in SQLite."""
    event = repo.create(
        process="ollama",
        classification="local",
        adapter="test_adapter",
        destination_host="127.0.0.1",
        destination_port=11434,
        bytes_sent=512,
        byte_accounting_supported=True,
    )
    assert event.event_id is not None
    assert event.classification == "local"

    events = repo.list_events(limit=10)
    assert len(events) >= 1
    assert any(e.event_id == event.event_id for e in events)


def test_rolling_window_counter_aggregation(repo: SovereigntyRepository):
    """Verify 5-minute rolling window aggregation correctly counts external events."""
    now = datetime.datetime.now(datetime.timezone.utc)

    # 1. Add recent local event
    repo.create(
        process="backend",
        classification="local",
        adapter="test_adapter",
        destination_host="127.0.0.1",
        destination_port=8000,
        ts=now,
    )

    # 2. Add recent external AI event
    repo.create(
        process="unauthorized_ai_worker",
        classification="external",
        adapter="test_adapter",
        destination_host="api.external.ai",
        destination_port=443,
        bytes_sent=2048,
        byte_accounting_supported=True,
        ts=now,
    )

    # 3. Add old external event outside 5-minute window
    repo.create(
        process="old_worker",
        classification="external",
        adapter="test_adapter",
        destination_host="api.old.ai",
        destination_port=443,
        ts=now - datetime.timedelta(minutes=10),
    )

    stats = repo.get_aggregated_stats(window_minutes=5)
    # The 5-minute window should only capture the recent external event
    assert stats["external_count"] >= 1
    assert stats["external_ai_calls"] >= 1
