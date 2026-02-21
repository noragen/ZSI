#!/usr/bin/env python
"""Optional mypy pilot runner (no hard dependency).

Behavior:
- If mypy is not installed: print info and exit 0 (unless --require-installed).
- If installed: run a focused pilot over selected modules/files.
"""

from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys

DEFAULT_TARGETS = [
    "ZSI/diagnostics.py",
    "ZSI/telemetry.py",
    "scripts/benchmark_snapshot.py",
    "scripts/build_dashboards.py",
    "scripts/security_scan_smoke.py",
    "scripts/zsi_call.py",
]


def _has_mypy() -> bool:
    return importlib.util.find_spec("mypy") is not None


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        action="append",
        dest="targets",
        default=[],
        help="Additional target file/module for mypy pilot.",
    )
    parser.add_argument(
        "--require-installed",
        action="store_true",
        help="Fail if mypy is not installed.",
    )
    parser.add_argument(
        "--strict-exit",
        action="store_true",
        help="Propagate mypy non-zero exit code.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if not _has_mypy():
        msg = "[mypy-pilot] mypy not installed; skipping optional pilot."
        print(msg)
        return 1 if args.require_installed else 0

    targets = DEFAULT_TARGETS + list(args.targets or [])
    cmd = [
        sys.executable,
        "-m",
        "mypy",
        "--ignore-missing-imports",
        "--follow-imports=silent",
        *targets,
    ]
    print("[mypy-pilot] running:", " ".join(cmd))
    rc = subprocess.call(cmd)
    if rc != 0 and not args.strict_exit:
        print("[mypy-pilot] non-zero result (kept non-blocking)")
        return 0
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
