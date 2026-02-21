#!/usr/bin/env python
"""Generate lightweight static dashboards from CI/local artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _fmt_bool(value: bool) -> str:
    return "PASS" if value else "FAIL"


def build_dashboard_markdown(
    benchmark_smoke: dict[str, Any] | None,
    benchmark_history: dict[str, Any] | None,
    include_release_note: bool = True,
) -> str:
    lines: list[str] = []
    lines.append("# ZSI CI Artifact Dashboard")
    lines.append("")
    lines.append("Lightweight snapshot for Security / Release / Performance artifacts.")
    lines.append("")

    lines.append("## Performance")
    if benchmark_smoke and benchmark_smoke.get("results"):
        lines.append("")
        lines.append("| Case | Mean (s) | Max (s) | Budget (s) | Status |")
        lines.append("| --- | ---: | ---: | ---: | --- |")
        for item in benchmark_smoke["results"]:
            lines.append(
                "| {name} | {mean:.3f} | {max:.3f} | {budget:.3f} | {status} |".format(
                    name=item.get("name", "?"),
                    mean=float(item.get("mean_seconds", 0.0)),
                    max=float(item.get("max_seconds", 0.0)),
                    budget=float(item.get("budget_seconds", 0.0)),
                    status=_fmt_bool(bool(item.get("ok", False))),
                )
            )
    else:
        lines.append("")
        lines.append("- No benchmark smoke artifact found.")

    lines.append("")
    lines.append("## Trend History")
    if benchmark_history:
        count = len(benchmark_history.get("history", []))
        lines.append("")
        lines.append(f"- History snapshots: `{count}`")
    else:
        lines.append("")
        lines.append("- No benchmark history artifact found.")

    lines.append("")
    lines.append("## Security")
    lines.append("")
    lines.append(
        "- Source artifacts: `test/test_security_scan_smoke.py`, "
        "`scripts/security_scan_smoke.py`"
    )
    lines.append("- CI gate: workflow job `security-scan-smoke`")

    lines.append("")
    lines.append("## Release")
    lines.append("")
    lines.append(
        "- Source artifacts: `scripts/check_release_gate.py`, "
        "`RELEASE.md`, `CHANGES`"
    )
    lines.append("- CI gate: workflow job `release-gates`")

    if include_release_note:
        lines.append("")
        lines.append("## Note")
        lines.append("")
        lines.append(
            "This dashboard is static and intended for quick inspection "
            "in PRs/artifacts."
        )

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--benchmark-smoke",
        default=".perf/benchmark-smoke.json",
        help="Path to benchmark smoke JSON artifact",
    )
    parser.add_argument(
        "--benchmark-history",
        default=".perf/benchmark-history.json",
        help="Path to benchmark history JSON artifact",
    )
    parser.add_argument(
        "--out",
        default="doc/ci-artifact-dashboard.md",
        help="Output markdown path",
    )
    args = parser.parse_args()

    smoke = _read_json(Path(args.benchmark_smoke))
    history = _read_json(Path(args.benchmark_history))
    content = build_dashboard_markdown(smoke, history)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    print(f"[dashboard] wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
