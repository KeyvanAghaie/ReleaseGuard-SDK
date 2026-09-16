"""Measure real local SDK overhead, not model latency or provider costs."""
import argparse
import asyncio
import json
import platform
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path

from releaseguard_sdk import InMemoryExporter, ReleaseGuard


def measure_sync(fn, iterations):
    start = time.perf_counter_ns()
    for _ in range(iterations):
        fn()
    return (time.perf_counter_ns() - start) / iterations / 1_000


async def measure_async(fn, iterations):
    start = time.perf_counter_ns()
    for _ in range(iterations):
        await fn()
    return (time.perf_counter_ns() - start) / iterations / 1_000


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=10_000)
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--output", default="benchmarks/results/local.json")
    args = parser.parse_args()
    if args.iterations < 1 or args.repeats < 1:
        parser.error("iterations and repeats must be positive")
    guard = ReleaseGuard(InMemoryExporter(max_spans=256))

    def plain():
        return 1

    async def plain_async():
        return 1

    observed = guard.observe(plain)
    observed_async = guard.observe(plain_async)
    for _ in range(1000):
        observed()

    async def samples():
        rows = []
        for _ in range(args.repeats):
            sync_base = measure_sync(plain, args.iterations)
            sync_observed = measure_sync(observed, args.iterations)
            async_base = await measure_async(plain_async, args.iterations)
            async_observed = await measure_async(observed_async, args.iterations)
            rows.append({
                "sync_plain_us": sync_base, "sync_observed_us": sync_observed,
                "async_plain_us": async_base, "async_observed_us": async_observed,
                "sync_overhead_us": sync_observed - sync_base,
                "async_overhead_us": async_observed - async_base,
            })
        return rows

    rows = asyncio.run(samples())
    result = {
        "kind": "measured-local-sdk-overhead",
        "timestamp": datetime.now(UTC).isoformat(),
        "python": platform.python_version(), "platform": platform.platform(),
        "processor": platform.processor(), "iterations": args.iterations,
        "repeats": args.repeats, "sdk_version": "0.1.0",
        "exporter": "bounded InMemoryExporter(256), oldest-first eviction",
        "unit": "microseconds_per_call",
        "median": {key: statistics.median(row[key] for row in rows) for key in rows[0]},
        "samples": rows,
        "limitations": "Single machine; no model or network calls; includes buffer export; "
        "does not establish production latency or throughput.",
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["median"], indent=2))


if __name__ == "__main__":
    main()
