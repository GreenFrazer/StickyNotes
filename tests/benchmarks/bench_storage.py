"""Benchmark StorageManager save/load at various note counts."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure project root is importable when run as script.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from stickynotes.storage import StorageManager
from tests.benchmarks._timing import run_timed
from tests.conftest import FakePaths

SMALL = "Short note text. " * 3
LARGE = "Long paragraph. " * 650  # ~10 KB


def _populate(storage: StorageManager, count: int, content: str) -> None:
    for i in range(count):
        nd = StorageManager.default_note()
        nd["content"] = f"{content} #{i}"
        storage.set_note(nd["id"], nd)


def run_benchmarks() -> list[dict]:
    results: list[dict] = []
    for count in (1, 10, 50, 100):
        for label, content in (("small", SMALL), ("large", LARGE)):
            base = Path("/tmp") / f"stickynotes_bench_{count}_{label}"
            paths = FakePaths(base)
            storage = StorageManager(paths, restore_prompt=lambda: False)
            _populate(storage, count, content)

            def do_save(s=storage) -> None:
                s.save()

            results.append(
                run_timed(
                    "storage_save",
                    f"{count}_notes_{label}",
                    do_save,
                    iterations=30 if count <= 10 else 10,
                )
            )

            def do_load(p=paths) -> None:
                StorageManager(p, restore_prompt=lambda: False)

            results.append(
                run_timed(
                    "storage_load",
                    f"{count}_notes_{label}",
                    do_load,
                    iterations=20 if count <= 50 else 5,
                )
            )
    return results


if __name__ == "__main__":
    import json

    print(json.dumps(run_benchmarks(), indent=2))
