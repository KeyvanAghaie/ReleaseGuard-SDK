"""Context-local instrumentation that preserves application return/raise semantics."""
import functools
import inspect
import logging
import secrets
import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Callable, Iterator, Literal

from .exporters import Exporter, InMemoryExporter
from .models import Pricing, Span, Usage

logger = logging.getLogger(__name__)
Source = Literal["live", "replay", "injected"]
Kind = Literal["internal", "llm"]


@dataclass
class _Active:
    trace_id: str
    span_id: str
    parent_id: str | None
    name: str
    kind: Kind
    source: Source
    start_ns: int
    start: datetime
    usage: Usage | None = None
    pricing: Pricing | None = None
    model: str | None = None
    errors: list[str] = field(default_factory=list)
    closed: bool = False


class ReleaseGuard:
    """Create one instance per application; collect() isolates each demo/request.

    Exporters are synchronous. Keep them fast; use your own bounded queue for
    network delivery. No inputs, outputs, or exception messages are captured.
    """

    def __init__(self, exporter: Exporter | None = None):
        self.exporter = exporter
        self._current: ContextVar[_Active | None] = ContextVar("rg_span", default=None)
        self._collector: ContextVar[InMemoryExporter | None] = ContextVar(
            "rg_collector", default=None
        )

    @contextmanager
    def collect(self, max_spans: int = 256) -> Iterator[InMemoryExporter]:
        """Collect locally instead of using the configured exporter."""
        collector = InMemoryExporter(max_spans)
        token = self._collector.set(collector)
        try:
            yield collector
        finally:
            self._collector.reset(token)

    def record_usage(
        self, *, model: str, usage: Usage, pricing: Pricing | None = None
    ) -> None:
        """Attach normalized usage to the current span. Last call wins."""
        active = self._current.get()
        if active is None or active.closed:
            raise RuntimeError("record_usage requires an active observed span")
        if not isinstance(usage, Usage) or not isinstance(model, str) or not 0 < len(model) <= 120:
            raise ValueError("Provide a Usage instance and a model name of 1–120 characters")
        if pricing is not None and not isinstance(pricing, Pricing):
            raise TypeError("pricing must be a Pricing instance")
        active.model, active.usage, active.pricing = model, usage, pricing

    @contextmanager
    def span(
        self, name: str, *, kind: Kind = "internal", source: Source = "live"
    ) -> Iterator[None]:
        if not isinstance(name, str) or not 0 < len(name) <= 120:
            raise ValueError("span name must contain 1–120 characters")
        if kind not in ("internal", "llm") or source not in ("live", "replay", "injected"):
            raise ValueError("Invalid span kind or source")
        parent = self._current.get()
        if parent is not None and parent.closed:
            parent = None
        active = _Active(
            trace_id=parent.trace_id if parent else secrets.token_hex(16),
            span_id=secrets.token_hex(8),
            parent_id=parent.span_id if parent else None,
            name=name, kind=kind, source=source,
            start_ns=time.perf_counter_ns(), start=datetime.now(UTC),
        )
        token = self._current.set(active)
        status, error_type = "ok", None
        try:
            yield
        except BaseException as exc:
            status = "error" if isinstance(exc, Exception) else "cancelled"
            error_type = type(exc).__name__
            raise
        finally:
            active.closed = True
            self._current.reset(token)
            # Export/serialization failures must not mask the user's result or exception.
            try:
                record = Span(
                    trace_id=active.trace_id, span_id=active.span_id,
                    parent_span_id=active.parent_id, name=name, kind=kind, source=source,
                    started_at=active.start, ended_at=datetime.now(UTC),
                    duration_ms=(time.perf_counter_ns() - active.start_ns) / 1_000_000,
                    status=status, error_type=error_type, model=active.model,
                    usage=active.usage,
                    estimated_cost_usd=active.pricing.estimate(active.usage)
                    if active.pricing is not None and active.usage is not None else None,
                    instrumentation_errors=tuple(active.errors),
                )
                target = self._collector.get()
                if target is None:
                    target = self.exporter
                if target is not None:
                    target.export(record)
            except Exception as exc:
                logger.warning("Telemetry export failed (%s)", type(exc).__name__)

    def observe(
        self,
        function: Callable | None = None,
        *,
        name: str | None = None,
        kind: Kind = "internal",
        source: Source = "live",
        usage_from: Callable[[Any], Usage | None] | None = None,
        model: str | None = None,
        pricing: Pricing | None = None,
    ):
        """Observe a sync/async function; optionally extract usage from its result."""
        def decorate(fn: Callable):
            if inspect.isgeneratorfunction(fn) or inspect.isasyncgenfunction(fn):
                raise TypeError("Streaming/generator instrumentation is not supported in v0.1")
            span_name = name or fn.__qualname__
            if not 0 < len(span_name) <= 120:
                raise ValueError("span name must contain 1–120 characters")
            if kind not in ("internal", "llm") or source not in ("live", "replay", "injected"):
                raise ValueError("Invalid span kind or source")
            if usage_from is not None and (model is None or not 0 < len(model) <= 120):
                raise ValueError("usage_from requires a model name of 1–120 characters")

            def extract(result):
                if usage_from is None:
                    return
                try:
                    usage = usage_from(result)
                    if usage is not None:
                        self.record_usage(model=model, usage=usage, pricing=pricing)
                except Exception as exc:
                    current = self._current.get()
                    if current is not None:
                        current.errors.append(type(exc).__name__)

            if inspect.iscoroutinefunction(fn):
                @functools.wraps(fn)
                async def async_wrapper(*args, **kwargs):
                    with self.span(span_name, kind=kind, source=source):
                        result = await fn(*args, **kwargs)
                        extract(result)
                        return result
                return async_wrapper

            @functools.wraps(fn)
            def sync_wrapper(*args, **kwargs):
                with self.span(span_name, kind=kind, source=source):
                    result = fn(*args, **kwargs)
                    extract(result)
                    return result
            return sync_wrapper

        return decorate(function) if function is not None else decorate

