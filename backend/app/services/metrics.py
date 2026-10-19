"""Helpers for measured service latency."""

from dataclasses import dataclass
from time import perf_counter


@dataclass
class Timer:
    started_at: float

    @classmethod
    def start(cls) -> "Timer":
        return cls(perf_counter())

    def elapsed_ms(self) -> float:
        return round((perf_counter() - self.started_at) * 1000, 2)
