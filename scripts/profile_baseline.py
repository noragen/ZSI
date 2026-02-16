#!/usr/bin/env python
"""Create cProfile baselines for core ZSI test entrypoints."""

from __future__ import annotations

import argparse
import os
import pstats
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = (
    ("test_zsi", ["test/test_zsi.py"]),
    ("wsdl2py_local", ["test/wsdl2py/runTests.py", "local"]),
)


def run_case(name: str, args: list[str], out_dir: Path, top_n: int) -> None:
    profile_file = out_dir / f"{name}.prof"
    cmd = [sys.executable, "-m", "cProfile", "-o", str(profile_file), *args]
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", ".")

    print(f"[profile] running {name}: {' '.join(cmd)}")
    subprocess.run(cmd, cwd=ROOT, env=env, check=True)

    print(f"[profile] top {top_n} cumulative functions for {name}:")
    stats = pstats.Stats(str(profile_file))
    stats.strip_dirs().sort_stats("cumulative").print_stats(top_n)
    print("")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        default=".perf",
        help="Directory for .prof outputs (default: .perf).",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=30,
        help="How many top cumulative entries to print per case.",
    )
    args = parser.parse_args()

    out_dir = (ROOT / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    for name, case_args in DEFAULT_CASES:
        run_case(name, list(case_args), out_dir, args.top)

    print(f"[profile] completed. Profiles written to: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
