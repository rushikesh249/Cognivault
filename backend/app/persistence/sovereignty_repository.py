"""Repository for Sovereignty and Network Events (TRD ?10.7, Component #19)."""

import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.persistence.models import SovereigntyEventORM, generate_uuid, get_utc_now


class SovereigntyRepository:
    """Thread-safe database operations for sovereignty and network events."""

    def __init__(self, session: Session):
        self._session = session

    def create(
        self,
        process: str,
        classification: str,
        adapter: str,
        destination_host: Optional[str] = None,
        destination_port: Optional[int] = None,
        bytes_sent: Optional[int] = None,
        byte_accounting_supported: bool = False,
        dns_observed: Optional[bool] = None,
        event_id: Optional[str] = None,
        ts: Optional[datetime.datetime] = None,
    ) -> SovereigntyEventORM:
        """Record a structured sovereignty network event."""
        now = ts or get_utc_now()
        event = SovereigntyEventORM(
            event_id=event_id or generate_uuid(),
            ts=now,
            process=process,
            destination_host=destination_host,
            destination_port=destination_port,
            classification=classification,
            bytes_sent=bytes_sent,
            byte_accounting_supported=byte_accounting_supported,
            dns_observed=dns_observed,
            adapter=adapter,
        )
        self._session.add(event)
        self._session.commit()
        self._session.refresh(event)
        return event

    def list_events(
        self,
        limit: int = 100,
        offset: int = 0,
        classification: Optional[str] = None,
    ) -> List[SovereigntyEventORM]:
        """Query events ordered by timestamp descending."""
        q = self._session.query(SovereigntyEventORM)
        if classification:
            q = q.filter(SovereigntyEventORM.classification == classification)
        return q.order_by(SovereigntyEventORM.ts.desc()).offset(offset).limit(limit).all()

    def get_aggregated_stats(
        self,
        window_minutes: Optional[int] = 5,
    ) -> Dict[str, Any]:
        """
        Aggregate event counts and data egress over rolling window.
        Returns external_ai_calls, external_embedding_calls, external_ocr_calls,
        successful_external_connections, total_bytes_sent, and byte_accounting_supported flag.
        """
        q = self._session.query(SovereigntyEventORM)
        if window_minutes is not None and window_minutes > 0:
            cutoff = get_utc_now() - datetime.timedelta(minutes=window_minutes)
            q = q.filter(SovereigntyEventORM.ts >= cutoff)

        events = q.all()

        external_count = 0
        external_ai_count = 0
        external_embedding_count = 0
        external_ocr_count = 0
        total_bytes = 0
        any_byte_accounting = False

        for ev in events:
            if ev.classification == "external":
                external_count += 1
                proc = (ev.process or "").lower()
                dest = (ev.destination_host or "").lower()

                # Check for specialized external process categorization if applicable
                if "embedding" in proc or "bge" in proc:
                    external_embedding_count += 1
                elif "ocr" in proc or "tesseract" in proc or "paddle" in proc:
                    external_ocr_count += 1
                else:
                    external_ai_count += 1

            if ev.bytes_sent is not None and ev.bytes_sent > 0:
                total_bytes += ev.bytes_sent
            if ev.byte_accounting_supported:
                any_byte_accounting = True

        data_egress_mb = round(total_bytes / (1024 * 1024), 4)

        return {
            "external_count": external_count,
            "external_ai_calls": external_ai_count,
            "external_embedding_calls": external_embedding_count,
            "external_ocr_calls": external_ocr_count,
            "successful_external_connections": external_count,
            "data_egress_mb": data_egress_mb,
            "byte_accounting_supported": any_byte_accounting,
            "total_events": len(events),
        }
