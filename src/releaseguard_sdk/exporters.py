"""Synchronous exporters: no implicit network access or background workers."""
from collections import deque
from threading import Lock
from typing import Protocol

from .models import Span


class Exporter(Protocol):
    def export(self, span: Span) -> None: ...


class InMemoryExporter:
    """A bounded, thread-safe buffer. Oldest spans are dropped when full."""

    def __init__(self, max_spans: int = 256):
        if max_spans < 1:
            raise ValueError("max_spans must be positive")
        self._spans: deque[Span] = deque(maxlen=max_spans)
        self._lock = Lock()
        self.dropped_spans = 0

    def export(self, span: Span) -> None:
        with self._lock:
            if len(self._spans) == self._spans.maxlen:
                self.dropped_spans += 1
            self._spans.append(span)

    def snapshot(self) -> list[Span]:
        with self._lock:
            return list(self._spans)

