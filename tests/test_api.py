import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient

from demo.api import app

client = TestClient(app)


def test_health():
    assert client.get("/api/health").json()["status"] == "ok"


@pytest.mark.parametrize("scenario,count,roots", [("success", 3, 1), ("failure", 3, 1),
                                                ("concurrent", 6, 2)])
def test_demo(scenario, count, roots):
    response = client.post("/api/demo", json={"scenario": scenario})
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "replay"
    assert len(data["spans"]) == count
    assert len({s["trace_id"] for s in data["spans"]}) == roots
    assert data["dropped_spans"] == 0
    if scenario == "failure":
        assert data["answers"] == []
        assert data["estimated_cost_usd"] is None
        assert sum(s["status"] == "error" for s in data["spans"]) == 2
    else:
        assert data["answers"]
        assert data["total_tokens"] == 246 * roots


@pytest.mark.parametrize("payload", [{"scenario": "arbitrary"}, {"prompt": "unbounded input"}])
def test_demo_rejects_unlisted_input(payload):
    assert client.post("/api/demo", json=payload).status_code == 422


def test_parallel_requests_do_not_share_spans():
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as session:
            return await asyncio.gather(*[
                session.post("/api/demo", json={"scenario": "success"}) for _ in range(8)
            ])
    responses = asyncio.run(run())
    traces = set()
    for response in responses:
        data = response.json()
        assert len(data["spans"]) == 3
        trace_id = data["spans"][0]["trace_id"]
        assert trace_id not in traces
        traces.add(trace_id)
