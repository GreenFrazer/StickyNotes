#!/usr/bin/env python3
"""Run all StickyNotes performance benchmarks and optionally save JSON."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.benchmarks import (  # noqa: E402
    bench_dock_poll,
    bench_dock_refresh,
    bench_note_expand,
    bench_scenarios,
    bench_storage,
)


def run_all() -> dict:
    results: list[dict] = []
    for module in (
        bench_storage,
        bench_dock_refresh,
        bench_note_expand,
        bench_dock_poll,
        bench_scenarios,
    ):
        results.extend(module.run_benchmarks())
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run StickyNotes benchmarks")
    parser.add_argument(
        "--save",
        type=Path,
        help="Write benchmark results to this JSON file",
    )
    args = parser.parse_args()
    payload = run_all()
    if args.save:
        args.save.parent.mkdir(parents=True, exist_ok=True)
        args.save.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"Saved {len(payload['results'])} benchmarks to {args.save}")
    else:
        print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
