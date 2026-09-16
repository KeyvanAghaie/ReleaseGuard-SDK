"""Bounded, request-local scenarios. No external API calls or user content."""
import asyncio
from decimal import Decimal
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict

from releaseguard_sdk import Pricing, ReleaseGuard, Span, Usage

app = FastAPI(title="ReleaseGuard SDK demo", version="0.1.0")
guard = ReleaseGuard()
DEMO_PRICING = Pricing(input_per_million=Decimal("1"), output_per_million=Decimal("3"))


class DemoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario: Literal["success", "failure", "concurrent"] = "success"


class DemoResponse(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    scenario: str
    mode: Literal["replay"] = "replay"
    notice: str
    spans: list[Span]
    answers: list[str]
    dropped_spans: int
    total_tokens: int
    estimated_cost_usd: Decimal | None
    duration_ms: float


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0", "mode": "replay"}


@app.post("/api/demo", response_model=DemoResponse)
async def run_demo(request: DemoRequest):
    @guard.observe(name="retrieve.context", source="replay")
    async def retrieve():
        await asyncio.sleep(0.025)
        return ["release-policy", "evaluation-guide"]

    @guard.observe(name="llm.generate", kind="llm", source="replay")
    async def generate():
        await asyncio.sleep(0.075)
        guard.record_usage(
            model="fixture-small", usage=Usage(input_tokens=184, output_tokens=62),
            pricing=DEMO_PRICING,
        )
        return "Evaluate the candidate against a fixed baseline before releasing."

    @guard.observe(name="llm.generate", kind="llm", source="injected")
    async def fail():
        await asyncio.sleep(0.045)
        raise TimeoutError("Injected provider timeout; not a real provider request.")

    @guard.observe(name="rag.answer", source="replay")
    async def answer(should_fail=False):
        await retrieve()
        return await (fail() if should_fail else generate())

    with guard.collect() as collector:
        if request.scenario == "concurrent":
            answers = await asyncio.gather(answer(), answer())
        else:
            try:
                answers = [await answer(request.scenario == "failure")]
            except TimeoutError:
                answers = []
    spans = sorted(collector.snapshot(), key=lambda span: span.started_at)
    llm_spans = [span for span in spans if span.kind == "llm"]
    known_costs = [span.estimated_cost_usd for span in llm_spans]
    roots = [span for span in spans if span.parent_span_id is None]
    return DemoResponse(
        scenario=request.scenario, spans=spans, answers=answers,
        notice="Live Python instrumentation over fixed responses and simulated delays. "
        "Token counts and USD rates are illustrative fixtures, not provider measurements.",
        dropped_spans=collector.dropped_spans,
        total_tokens=sum(span.usage.total_tokens for span in llm_spans if span.usage),
        estimated_cost_usd=sum(known_costs, Decimal(0))
        if known_costs and all(cost is not None for cost in known_costs) else None,
        duration_ms=max((span.duration_ms for span in roots), default=0),
    )

