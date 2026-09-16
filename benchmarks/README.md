# SDK overhead benchmark

Run from the repository root after installing the package:

```shell
python benchmarks/overhead.py --iterations 10000 --repeats 7
```

The script warms the synchronous observed path, then measures plain and observed
sync/async no-op calls. It writes every batch and median microseconds per call
to results/local.json, with timestamp, Python version, platform and iteration
counts. Overhead is the observed minus plain duration for each batch.

The bounded in-memory exporter is included; network export, LLM calls and provider
billing are not. Interpret this as a local microbenchmark, not a production SLA.
Tiny no-op baseline ratios are misleading; compare absolute added microseconds.
Results vary by hardware, runtime load and OS. Async runs have no separate warmup.

The web demo is different: its latency includes simulated sleeps, and its token
and price metadata is illustrative. Do not present those as live LLM measurements.

