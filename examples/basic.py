"""Run after installing: python examples/basic.py"""
import asyncio

from releaseguard_sdk import Pricing, ReleaseGuard, openai_usage

guard = ReleaseGuard()


@guard.observe(
    name="llm.generate", kind="llm", source="replay",
    usage_from=openai_usage, model="fixture-small",
    pricing=Pricing(input_per_million="1", output_per_million="3"),
)
async def generate():
    await asyncio.sleep(0.01)
    return {"text": "A fixed response.", "usage": {"input_tokens": 100, "output_tokens": 20}}


@guard.observe(name="answer", source="replay")
async def answer():
    return await generate()


async def main():
    with guard.collect() as traces:
        await answer()
    for span in traces.snapshot():
        print(span.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())

