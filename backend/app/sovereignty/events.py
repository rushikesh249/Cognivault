"""Sovereignty Event and Status Schemas (TRD ?9 Table 20, ?10.7 Table 27, ?24 Table 52)."""

import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class ConnectionRecord(BaseModel):
    """Raw network connection record inspected from OS socket/process table."""
    process: str = Field(default="backend", description="Process name or identifier")
    pid: Optional[int] = Field(default=None, description="Operating system process ID")
    local_address: str = Field(default="127.0.0.1", description="Source IP address")
    local_port: Optional[int] = Field(default=None, description="Source port")
    remote_address: Optional[str] = Field(default=None, description="Destination IP address or hostname")
    remote_port: Optional[int] = Field(default=None, description="Destination port")
    state: str = Field(default="ESTABLISHED", description="Socket state (ESTABLISHED, SYN_SENT, TIME_WAIT, etc.)")
    bytes_sent: Optional[int] = Field(default=None, description="Bytes transmitted on this connection if available")
    byte_accounting_supported: bool = Field(default=False, description="Whether the OS adapter measures bytes")


class SovereigntyEvent(BaseModel):
    """Structured sovereignty network event (TRD Section 24, Table 52)."""
    event_id: str
    ts: datetime.datetime
    process: str
    destination_host: Optional[str] = None
    destination_port: Optional[int] = None
    classification: Literal["local", "external", "blocked"]
    bytes_sent: Optional[int] = None
    byte_accounting_supported: bool = False
    dns_observed: Optional[bool] = None
    adapter: str


class SovereigntyStatus(BaseModel):
    """Live sovereignty counters and subsystem health flags (TRD Section 9, Table 20)."""

    # --- Required TRD Table 20 top-level fields ---
    external_ai_calls: int = Field(default=0, ge=0, description="Count of external AI API calls detected")
    external_embedding_calls: int = Field(default=0, ge=0, description="Count of external embedding API calls detected")
    external_ocr_calls: int = Field(default=0, ge=0, description="Count of external OCR API calls detected")
    data_egress_mb: float = Field(default=0.0, ge=0.0, description="Total megabytes of data egress detected")
    local_inference: Literal["ok", "degraded"] = Field(default="ok", description="Status of local Ollama inference")
    local_ocr: Literal["ok", "degraded"] = Field(default="ok", description="Status of local PaddleOCR engine")
    local_rag: Literal["ok", "degraded"] = Field(default="ok", description="Status of local ChromaDB and embedding engine")
    local_vision: Literal["ok", "degraded"] = Field(default="ok", description="Status of local Vision-Language Model")
    local_sandbox: Literal["ok", "degraded"] = Field(default="ok", description="Status of Docker sandbox isolation")
    monitor_status: Literal["ok", "degraded"] = Field(default="ok", description="Status of the Sovereignty Monitor thread")

    # --- Supplementary monitoring fields (ADR-012 byte accounting invariant) ---
    byte_accounting_supported: bool = Field(
        default=False,
        description=(
            "Whether the OS adapter supports actual byte-level accounting. "
            "When False, data_egress_mb is NOT proof of zero egress."
        ),
    )
    external_connections_5m: int = Field(
        default=0, ge=0,
        description="Total external connections detected in rolling 5-minute window",
    )
    external_dns_lookups_5m: int = Field(
        default=0, ge=0,
        description="Total external DNS lookups detected in rolling 5-minute window",
    )
