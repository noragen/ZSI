#!/usr/bin/env python
"""Minimal security helper to validate untrusted resolver URIs."""

from __future__ import annotations

import argparse
import re
import sys
from urllib.parse import urlsplit

BLOCKED_SCHEMES = {
    "file",
    "ftp",
    "gopher",
    "data",
    "javascript",
    "jar",
}


def validate_untrusted_uri(
    uri: str,
    allow_prefixes: tuple[str, ...] = (),
    allowed_schemes: tuple[str, ...] = ("https",),
) -> None:
    """Validate a URI before handing it to network-based resolvers.

    Raises ValueError if URI violates hardening constraints.
    """
    if not isinstance(uri, str):
        raise ValueError("URI must be a string")

    value = uri.strip()
    if not value:
        raise ValueError("URI must not be empty")

    if value != uri:
        raise ValueError("URI must not have leading or trailing whitespace")

    if re.search(r"[\x00-\x1f\x7f]", value):
        raise ValueError("URI must not contain control characters")

    parsed = urlsplit(value)
    scheme = parsed.scheme.lower()
    if not scheme:
        raise ValueError("URI must be absolute and include a scheme")

    if scheme in BLOCKED_SCHEMES:
        raise ValueError(f"URI scheme is blocked: {scheme}")

    normalized_allowed = tuple(s.lower() for s in allowed_schemes)
    if scheme not in normalized_allowed:
        raise ValueError(f"URI scheme is not allowed: {scheme}")

    if not parsed.netloc:
        raise ValueError("URI must include a network location")

    if parsed.username or parsed.password:
        raise ValueError("URI must not include embedded credentials")

    if allow_prefixes and not any(value.startswith(prefix) for prefix in allow_prefixes):
        raise ValueError("URI does not match an allowed prefix")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate resolver URI hardening constraints"
    )
    parser.add_argument("--uri", required=True, help="URI to validate")
    parser.add_argument(
        "--allow-prefix",
        action="append",
        default=[],
        help="Allowed trusted URI prefix (repeatable)",
    )
    parser.add_argument(
        "--allow-scheme",
        action="append",
        default=["https"],
        help="Allowed URI scheme (repeatable, default: https)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        validate_untrusted_uri(
            args.uri,
            allow_prefixes=tuple(args.allow_prefix),
            allowed_schemes=tuple(args.allow_scheme),
        )
    except ValueError as exc:
        print(f"[security-uri-check] FAIL: {exc}")
        return 1

    print("[security-uri-check] OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
