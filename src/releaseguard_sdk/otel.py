"""Bridge completed ReleaseGuard spans to an OpenTelemetry SpanExporter.

Install releaseguard-sdk[otel]. The caller owns exporter shutdown/flush.
Export is synchronous; OTLP exporters can add network latency.
"""
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.trace import SpanContext, SpanKind, Status, StatusCode, TraceFlags

from .models import Span


class OpenTelemetryExporter:
    def __init__(self, exporter: SpanExporter, service_name: str = "releaseguard"):
        self.exporter = exporter
        self.resource = Resource.create({"service.name": service_name})

    def export(self, span: Span) -> None:
        def context(span_id: str) -> SpanContext:
            return SpanContext(
                trace_id=int(span.trace_id, 16), span_id=int(span_id, 16),
                is_remote=False, trace_flags=TraceFlags(TraceFlags.SAMPLED),
            )
        attributes = {
            "releaseguard.schema_version": span.schema_version,
            "releaseguard.source": span.source,
            "releaseguard.duration_ms": span.duration_ms,
        }
        if span.model is not None:
            attributes["gen_ai.request.model"] = span.model
        if span.usage is not None:
            attributes["gen_ai.usage.input_tokens"] = span.usage.input_tokens
            attributes["gen_ai.usage.output_tokens"] = span.usage.output_tokens
        if span.estimated_cost_usd is not None:
            attributes["releaseguard.estimated_cost_usd"] = float(span.estimated_cost_usd)
        if span.error_type is not None:
            attributes["error.type"] = span.error_type
        record = ReadableSpan(
            name=span.name, context=context(span.span_id),
            parent=context(span.parent_span_id) if span.parent_span_id else None,
            resource=self.resource,
            attributes=attributes,
            kind=SpanKind.CLIENT if span.kind == "llm" else SpanKind.INTERNAL,
            status=Status(StatusCode.OK if span.status == "ok" else StatusCode.ERROR),
            start_time=int(span.started_at.timestamp() * 1_000_000_000),
            end_time=int(span.started_at.timestamp() * 1_000_000_000)
            + int(span.duration_ms * 1_000_000),
            instrumentation_scope=InstrumentationScope("releaseguard-sdk", "0.1.0"),
        )
        if self.exporter.export((record,)) is SpanExportResult.FAILURE:
            raise RuntimeError("OpenTelemetry exporter rejected span")

