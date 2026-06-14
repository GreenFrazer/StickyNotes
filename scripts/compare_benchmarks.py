#!/usr/bin/env python3
"""Compare two benchmark JSON files and emit a markdown report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REGRESSION_THRESHOLD = 0.05  # fail if >5% slower


def _key(entry: dict) -> tuple[str, str]:
    return (entry["name"], entry["scenario"])


def _index(results: list[dict]) -> dict[tuple[str, str], dict]:
    return {_key(r): r for r in results}


def compare(baseline: dict, current: dict) -> tuple[str, bool]:
    base_idx = _index(baseline.get("results", []))
    cur_idx = _index(current.get("results", []))
    lines = [
        "# Benchmark comparison",
        "",
        f"- Baseline: `{baseline.get('generated_at', 'unknown')}`",
        f"- Current: `{current.get('generated_at', 'unknown')}`",
        "",
        "| Benchmark | Scenario | Baseline (ms) | Current (ms) | Delta | Status |",
        "|-----------|----------|---------------|--------------|-------|--------|",
    ]
    failed = False
    all_keys = sorted(set(base_idx) | set(cur_idx))
    for key in all_keys:
        name, scenario = key
        b = base_idx.get(key)
        c = cur_idx.get(key)
        if b is None or c is None:
            lines.append(
                f"| {name} | {scenario} | — | — | missing | SKIP |"
            )
            continue
        b_med = b["median_ms"]
        c_med = c["median_ms"]
        if b_med == 0:
            delta_pct = 0.0 if c_med == 0 else 100.0
        else:
            delta_pct = ((c_med - b_med) / b_med) * 100.0
        if delta_pct > REGRESSION_THRESHOLD * 100:
            status = "FAIL"
            failed = True
        elif delta_pct < -1:
            status = "faster"
        else:
            status = "OK"
        sign = "+" if delta_pct >= 0 else ""
        lines.append(
            f"| {name} | {scenario} | {b_med:.4f} | {c_med:.4f} | "
            f"{sign}{delta_pct:.1f}% | {status} |"
        )
    lines.append("")
    if failed:
        lines.append(
            f"**Result: FAIL** — one or more scenarios regressed by more than "
            f"{REGRESSION_THRESHOLD * 100:.0f}%."
        )
    else:
        lines.append("**Result: PASS** — no scenario regressed beyond threshold.")
    return "\n".join(lines) + "\n", failed


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare benchmark JSON files")
    parser.add_argument("baseline", type=Path)
    parser.add_argument("current", type=Path)
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("benchmarks/report.md"),
        help="Write markdown report to this path",
    )
    args = parser.parse_args()
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    current = json.loads(args.current.read_text(encoding="utf-8"))
    report, failed = compare(baseline, current)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
