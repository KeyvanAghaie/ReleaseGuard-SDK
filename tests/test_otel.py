from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from releaseguard_sdk import ReleaseGuard
from releaseguard_sdk.otel import OpenTelemetryExporter


def test_bridge_preserves_ids_parent_and_status():
    memory = InMemorySpanExporter()
    guard = ReleaseGuard(OpenTelemetryExporter(memory))

    @guard.observe(kind="llm", source="replay")
    def child():
        return 1

    @guard.observe
    def parent():
        return child()

    assert parent() == 1
    child_span, root = memory.get_finished_spans()
    assert child_span.parent.span_id == root.context.span_id
    assert child_span.context.trace_id == root.context.trace_id
    assert child_span.attributes["releaseguard.source"] == "replay"
    assert child_span.resource.attributes["service.name"] == "releaseguard"
    assert child_span.end_time >= child_span.start_time
