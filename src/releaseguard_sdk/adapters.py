"""Optional normalization helpers; no provider SDK is imported."""
from collections.abc import Mapping
from typing import Any

from .models import Usage


def openai_usage(response: Any) -> Usage | None:
    """Read Responses or Chat Completions usage from a mapping or SDK object.

    Missing usage remains unknown. Incomplete/invalid usage raises a validation
    error, captured as instrumentation_errors when used with @observe.
    """
    def get(value, key):
        return value.get(key) if isinstance(value, Mapping) else getattr(value, key, None)

    usage = get(response, "usage")
    if usage is None:
        return None
    input_tokens = get(usage, "input_tokens")
    output_tokens = get(usage, "output_tokens")
    if input_tokens is None:
        input_tokens = get(usage, "prompt_tokens")
    if output_tokens is None:
        output_tokens = get(usage, "completion_tokens")
    return Usage(input_tokens=input_tokens, output_tokens=output_tokens)

