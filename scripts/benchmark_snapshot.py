#!/usr/bin/env python
"""Compare benchmark smoke output against historical trend snapshots."""

from __future__ import annotations

import argparse
import datetime as _dt
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _index_results(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["name"]: item for item in payload.get("results", [])}


def _median(values: list[float]) -> float:
    items = sorted(values)
    n = len(items)
    mid = n // 2
    if n % 2:
        return items[mid]
    return (items[mid - 1] + items[mid]) / 2.0


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def compare_to_history(
    current: dict[str, Any],
    history: list[dict[str, Any]],
    warn_regression: float,
    min_history: int,
) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    info: list[str] = []
    by_name = _index_results(current)

    for name, row in by_name.items():
        historical_values: list[float] = []
        for snap in history:
            hist_row = _index_results(snap.get("payload", {})).get(name)
            if not hist_row:
                continue
            historical_values.append(_to_float(hist_row.get("mean_seconds")))

        if len(historical_values) < min_history:
            info.append(
                f"{name}: insufficient history "
                f"({len(historical_values)}/{min_history})"
            )
            continue

        baseline = _median(historical_values)
        current_mean = _to_float(row.get("mean_seconds"))
        if baseline <= 0:
            continue
        delta_ratio = (current_mean - baseline) / baseline
        if delta_ratio > warn_regression:
            warnings.append(
                f"{name}: mean {current_mean:.3f}s vs median {baseline:.3f}s "
                f"(+{delta_ratio * 100:.1f}%)"
            )
        else:
            info.append(
                f"{name}: mean {current_mean:.3f}s vs median {baseline:.3f}s "
                f"({delta_ratio * 100:.1f}%)"
            )

    return warnings, info


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--current",
        default=".perf/benchmark-smoke.json",
        help="Current benchmark smoke JSON file.",
    )
    parser.add_argument(
        "--history",
        default=".perf/benchmark-history.json",
        help="History JSON file used for trend comparison.",
    )
    parser.add_argument(
        "--warn-regression",
        type=float,
        default=0.20,
        help="Warn threshold as ratio (0.20 = 20%% regression).",
    )
    parser.add_argument(
        "--min-history",
        type=int,
        default=3,
        help="Minimum number of history points per benchmark to compare trends.",
    )
    parser.add_argument(
        "--update-history",
        action="store_true",
        help="Append current benchmark snapshot into history file.",
    )
    parser.add_argument(
        "--fail-on-warning",
        action="store_true",
        help="Return non-zero when regression warnings are detected.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    current_path = Path(args.current).resolve()
    history_path = Path(args.history).resolve()

    current = _load_json(current_path)
    if history_path.exists():
        history_data = _load_json(history_path)
        history = history_data.get("history", [])
    else:
        history_data = {"history": []}
        history = []

    warnings, info = compare_to_history(
        current=current,
        history=history,
        warn_regression=args.warn_regression,
        min_history=args.min_history,
    )

    for line in info:
        print(f"[bench-snapshot] INFO: {line}")

    if warnings:
        print("[bench-snapshot] WARN:")
        for line in warnings:
            print(f" - {line}")
    else:
        print("[bench-snapshot] OK: no regression warnings")

    if args.update_history:
        history_data["history"].append(
            {
                "timestamp": _dt.datetime.now(_dt.timezone.utc).isoformat(),
                "payload": current,
            }
        )
        history_path.parent.mkdir(parents=True, exist_ok=True)
        history_path.write_text(json.dumps(history_data, indent=2), encoding="utf-8")
        print(f"[bench-snapshot] updated history: {history_path}")

    if warnings and args.fail_on_warning:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
