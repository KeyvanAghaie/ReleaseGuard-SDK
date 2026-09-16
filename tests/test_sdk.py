import asyncio
from decimal import Decimal

import pytest
from pydantic import ValidationError

from releaseguard_sdk import InMemoryExporter, Pricing, ReleaseGuard, Span, Usage, openai_usage


def test_nested_sync_preserves_identity_metadata_and_parent():
    guard = ReleaseGuard()
    result = object()

    @guard.observe
    def child(value):
        """Public function docstring."""
        return value

    @guard.observe
    def parent():
        return child(result)

    with guard.collect() as collector:
        assert parent() is result
    spans = collector.snapshot()
    assert child.__name__ == "child"
    assert child.__doc__ == "Public function docstring."
    assert len(spans) == 2
    assert spans[0].parent_span_id == spans[1].span_id
    assert spans[0].trace_id == spans[1].trace_id
    assert spans[1].parent_span_id is None
    assert all(s.duration_ms >= 0 and s.status == "ok" for s in spans)
    assert Span.model_validate_json(spans[0].model_dump_json()) == spans[0]


def test_async_concurrency_isolates_roots_and_links_children():
    guard = ReleaseGuard()

    @guard.observe
    async def child():
        await asyncio.sleep(0)
        return 42

    @guard.observe
    async def parent():
        return await child()

    async def run():
        with guard.collect() as collector:
            assert await asyncio.gather(*(parent() for _ in range(20))) == [42] * 20
        return collector.snapshot()

    spans = asyncio.run(run())
    roots = {s.span_id: s for s in spans if s.parent_span_id is None}
    assert len(roots) == 20
    assert len({s.trace_id for s in roots.values()}) == 20
    assert len(spans) == 40
    for span in spans:
        if span.parent_span_id:
            assert span.trace_id == roots[span.parent_span_id].trace_id


def test_exceptions_preserved_and_private_content_not_collected():
    guard = ReleaseGuard()
    error = ValueError("secret-password-123")

    @guard.observe
    def fail(secret):
        raise error

    with guard.collect() as collector:
        with pytest.raises(ValueError) as caught:
            fail("sensitive-prompt")
    assert caught.value is error
    span = collector.snapshot()[0]
    assert span.status == "error"
    assert span.error_type == "ValueError"
    assert "secret-password" not in span.model_dump_json()
    assert "sensitive-prompt" not in span.model_dump_json()


def test_async_cancellation_propagates_and_resets_context():
    guard = ReleaseGuard()

    @guard.observe
    async def cancelled():
        raise asyncio.CancelledError()

    @guard.observe
    async def healthy():
        return True

    async def run():
        with guard.collect() as collector:
            with pytest.raises(asyncio.CancelledError):
                await cancelled()
            assert await healthy()
        return collector.snapshot()

    first, second = asyncio.run(run())
    assert first.status == "cancelled"
    assert second.parent_span_id is None
    assert first.trace_id != second.trace_id


def test_export_failure_does_not_mask_result_or_error(caplog):
    class BrokenExporter:
        def export(self, span):
            raise RuntimeError("secret-exporter-credential")

    guard = ReleaseGuard(BrokenExporter())

    @guard.observe
    def good():
        return 7

    @guard.observe
    def bad():
        raise KeyError("original")

    assert good() == 7
    with pytest.raises(KeyError):
        bad()
    assert "Telemetry export failed" in caplog.text
    assert "secret-exporter-credential" not in caplog.text


def test_usage_and_decimal_pricing_and_unknown_are_distinct():
    guard = ReleaseGuard()
    pricing = Pricing(input_per_million="1", output_per_million="3")

    @guard.observe(
        usage_from=openai_usage, model="fixture", pricing=pricing, kind="llm", source="replay"
    )
    def call():
        return {"usage": {"prompt_tokens": 184, "completion_tokens": 62}}

    @guard.observe
    def no_usage():
        return "ok"

    with guard.collect() as collector:
        call()
        no_usage()
    known, unknown = collector.snapshot()
    assert known.usage.total_tokens == 246
    assert known.estimated_cost_usd == Decimal("0.000370")
    assert unknown.usage is None
    assert unknown.estimated_cost_usd is None


def test_bad_usage_extractor_preserves_result_and_reports_problem():
    guard = ReleaseGuard()
    result = {"usage": {"input_tokens": -1, "output_tokens": 2}}

    @guard.observe(usage_from=openai_usage, model="fixture")
    def call():
        return result

    with guard.collect() as collector:
        assert call() is result
    span = collector.snapshot()[0]
    assert span.status == "ok"
    assert span.usage is None
    assert span.instrumentation_errors == ("ValidationError",)


def test_bounded_collector_and_nested_collectors():
    default = InMemoryExporter()
    guard = ReleaseGuard(default)

    @guard.observe
    def call():
        return None

    with guard.collect(max_spans=2) as outer:
        call()
        with guard.collect() as inner:
            call()
        call()
        call()
    call()
    assert len(outer.snapshot()) == 2
    assert outer.dropped_spans == 1
    assert len(inner.snapshot()) == 1
    assert len(default.snapshot()) == 1


def test_collectors_are_request_local():
    guard = ReleaseGuard()

    @guard.observe
    async def call():
        await asyncio.sleep(0)

    async def request():
        with guard.collect() as collector:
            await call()
        return collector.snapshot()

    async def run():
        return await asyncio.gather(request(), request())

    first, second = asyncio.run(run())
    assert len(first) == len(second) == 1
    assert first[0].trace_id != second[0].trace_id


@pytest.mark.parametrize("tokens", [-1, 1.5, True, "2"])
def test_usage_rejects_invalid_counts(tokens):
    with pytest.raises(ValidationError):
        Usage(input_tokens=tokens, output_tokens=0)


@pytest.mark.parametrize("price", ["NaN", "Infinity", "-1"])
def test_pricing_rejects_invalid_values(price):
    with pytest.raises(ValidationError):
        Pricing(input_per_million=price, output_per_million=0)


def test_usage_normalizes_objects_and_absent_usage():
    from types import SimpleNamespace
    response = SimpleNamespace(usage=SimpleNamespace(input_tokens=0, output_tokens=0))
    assert openai_usage(response) == Usage(input_tokens=0, output_tokens=0)
    assert openai_usage({"text": "no metadata"}) is None


def test_generator_rejected_instead_of_recording_creation_time():
    guard = ReleaseGuard()
    with pytest.raises(TypeError):
        @guard.observe
        def stream():
            yield "token"


def test_manual_usage_requires_active_span():
    with pytest.raises(RuntimeError):
        ReleaseGuard().record_usage(model="x", usage=Usage(input_tokens=1, output_tokens=1))


def test_child_started_after_parent_finishes_becomes_new_trace():
    guard = ReleaseGuard()
    tasks = []

    @guard.observe
    async def child():
        return None

    @guard.observe
    async def parent(event):
        async def later():
            await event.wait()
            await child()
        tasks.append(asyncio.create_task(later()))

    async def run():
        event = asyncio.Event()
        with guard.collect() as collector:
            await parent(event)
            event.set()
            await tasks[0]
        return collector.snapshot()

    parent_span, child_span = asyncio.run(run())
    assert child_span.parent_span_id is None
    assert parent_span.trace_id != child_span.trace_id
