"""Versioned, content-free telemetry contracts."""
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Contract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)


class Usage(Contract):
    input_tokens: int = Field(ge=0, strict=True)
    output_tokens: int = Field(ge=0, strict=True)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class Pricing(Contract):
    """Caller-supplied USD per million tokens; never a live provider price."""
    input_per_million: Decimal = Field(ge=0)
    output_per_million: Decimal = Field(ge=0)

    def estimate(self, usage: Usage) -> Decimal:
        return (
            self.input_per_million * usage.input_tokens
            + self.output_per_million * usage.output_tokens
        ) / Decimal(1_000_000)


class Span(Contract):
    schema_version: Literal["1.0"] = "1.0"
    trace_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    span_id: str = Field(pattern=r"^[0-9a-f]{16}$")
    parent_span_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{16}$")
    name: str = Field(min_length=1, max_length=120)
    kind: Literal["internal", "llm"] = "internal"
    source: Literal["live", "replay", "injected"] = "live"
    started_at: datetime
    ended_at: datetime
    duration_ms: float = Field(ge=0)
    status: Literal["ok", "error", "cancelled"]
    error_type: str | None = None
    model: str | None = Field(default=None, max_length=120)
    usage: Usage | None = None
    estimated_cost_usd: Decimal | None = Field(default=None, ge=0)
    instrumentation_errors: tuple[str, ...] = ()

