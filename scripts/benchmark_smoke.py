#!/usr/bin/env python
"""Simple runtime smoke benchmark for core test entrypoints."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    cmd: list[str]
    budget_seconds: float


def default_cases() -> list[BenchmarkCase]:
    return [
        BenchmarkCase("test_zsi", [sys.executable, "test/test_zsi.py"], 30.0),
        BenchmarkCase(
            "wsdl2py_local",
            [sys.executable, "test/wsdl2py/runTests.py", "local"],
            180.0,
        ),
    ]


def run_once(case: BenchmarkCase) -> float:
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", ".")
    start = time.perf_counter()
    subprocess.run(case.cmd, cwd=ROOT, env=env, check=True)
    return time.perf_counter() - start


def run_case(case: BenchmarkCase, runs: int) -> dict:
    samples = []
    for idx in range(runs):
        duration = run_once(case)
        samples.append(duration)
        print(f"[bench] {case.name} run {idx + 1}/{runs}: {duration:.3f}s")

    mean = statistics.mean(samples)
    max_t = max(samples)
    min_t = min(samples)
    ok = max_t <= case.budget_seconds
    return {
        "name": case.name,
        "runs": runs,
        "budget_seconds": case.budget_seconds,
        "min_seconds": min_t,
        "mean_seconds": mean,
        "max_seconds": max_t,
        "ok": ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=2, help="Runs per case.")
    parser.add_argument(
        "--json-out",
        default=".perf/benchmark-smoke.json",
        help="Path to write JSON summary.",
    )
    args = parser.parse_args()

    out_path = (ROOT / args.json_out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    results = [run_case(case, args.runs) for case in default_cases()]
    payload = {"results": results}
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[bench] wrote summary: {out_path}")

    failed = [r for r in results if not r["ok"]]
    if failed:
        print("[bench] budget exceeded for:")
        for row in failed:
            msg = (
                f"  - {row['name']}: max {row['max_seconds']:.3f}s > budget "
                f"{row['budget_seconds']:.3f}s"
            )
            print(msg)
        return 1

    print("[bench] all benchmark budgets satisfied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
