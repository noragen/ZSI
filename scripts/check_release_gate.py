#!/usr/bin/env python
"""Release gate checks for CI tag builds.

Checks:
- tag format starts with 'v'
- RELEASE.md exists and has a checklist section
- CHANGES mentions the release version (without leading 'v')
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def fail(message: str) -> int:
    print(f"[release-gate] FAIL: {message}")
    return 1


def ok(message: str) -> None:
    print(f"[release-gate] OK: {message}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate release gate documents")
    parser.add_argument("--tag", required=True, help="git tag, e.g. v2.1.0")
    args = parser.parse_args()

    tag = args.tag.strip()
    if not tag.startswith("v"):
        return fail("tag must start with 'v'")

    # Accept stable and common prerelease tag forms.
    # Examples: v2.1.0, v2.1.0-rc1, v2.1.0-a1, v2.1.0-b1
    if not re.match(r"^v\d+\.\d+\.\d+(?:-(?:rc|a|b)\d+)?$", tag):
        return fail(f"tag format not recognized: {tag}")

    version = tag[1:]

    release_md = Path("RELEASE.md")
    if not release_md.exists():
        return fail("RELEASE.md missing")
    release_text = release_md.read_text(encoding="utf-8", errors="replace")
    if "Release Checklist" not in release_text:
        return fail("RELEASE.md missing 'Release Checklist' section")
    ok("RELEASE.md structure looks good")

    changes = Path("CHANGES")
    if not changes.exists():
        return fail("CHANGES missing")
    changes_text = changes.read_text(encoding="utf-8", errors="replace")
    if version not in changes_text:
        return fail(f"CHANGES does not mention version {version}")
    ok(f"CHANGES mentions version {version}")

    ok(f"all release checks passed for tag {tag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
