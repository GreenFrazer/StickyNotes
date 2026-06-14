"""Shared timing helpers for benchmarks."""

from __future__ import annotations

import statistics
import time
from collections.abc import Callable
from typing import Any


def run_timed(
    name: str,
    scenario: str,
    fn: Callable[[], None],
    *,
    iterations: int = 50,
    warmup: int = 3,
) -> dict[str, Any]:
    for _ in range(warmup):
        fn()
    samples: list[float] = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t0) * 1000.0)
    samples.sort()
    p95_idx = min(len(samples) - 1, int(len(samples) * 0.95))
    return {
        "name": name,
        "scenario": scenario,
        "median_ms": round(statistics.median(samples), 4),
        "p95_ms": round(samples[p95_idx], 4),
        "iterations": iterations,
    }
