#!/usr/bin/env python
"""Minimal security helper to validate untrusted resolver URIs."""

from __future__ import annotations

import argparse
import ipaddress
import re
import sys
from urllib.parse import urlsplit

try:
    from scripts.security_policy_defaults import (
        DEFAULT_ALLOWED_SCHEMES,
        DEFAULT_BLOCKED_SCHEMES,
        load_policy_defaults,
        normalize_schemes,
    )
except ImportError:  # pragma: no cover - fallback for direct script execution
    from security_policy_defaults import (  # type: ignore
        DEFAULT_ALLOWED_SCHEMES,
        DEFAULT_BLOCKED_SCHEMES,
        load_policy_defaults,
        normalize_schemes,
    )

BLOCKED_SCHEMES = set(DEFAULT_BLOCKED_SCHEMES)


def validate_untrusted_uri(
    uri: str,
    allow_prefixes: tuple[str, ...] = (),
    allowed_schemes: tuple[str, ...] = DEFAULT_ALLOWED_SCHEMES,
    blocked_schemes: tuple[str, ...] | set[str] | frozenset[str] = (
        DEFAULT_BLOCKED_SCHEMES
    ),
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

    normalized_blocked = set(normalize_schemes(tuple(blocked_schemes)))
    if scheme in normalized_blocked:
        raise ValueError(f"URI scheme is blocked: {scheme}")

    normalized_allowed = normalize_schemes(allowed_schemes)
    if scheme not in normalized_allowed:
        raise ValueError(f"URI scheme is not allowed: {scheme}")

    if not parsed.netloc:
        raise ValueError("URI must include a network location")

    if parsed.username or parsed.password:
        raise ValueError("URI must not include embedded credentials")

    hostname = (parsed.hostname or "").strip().lower()
    if hostname:
        if hostname == "localhost" or hostname.endswith(".localhost"):
            raise ValueError("URI host is blocked by SSRF policy")
        try:
            host_ip = ipaddress.ip_address(hostname)
        except ValueError:
            host_ip = None
        if host_ip is not None:
            if host_ip.is_loopback:
                raise ValueError("URI loopback address is blocked by SSRF policy")
            if host_ip == ipaddress.ip_address("169.254.169.254"):
                raise ValueError("URI metadata address is blocked by SSRF policy")
            if host_ip.is_private:
                raise ValueError("URI private address is blocked by SSRF policy")

    if allow_prefixes and not any(
        value.startswith(prefix) for prefix in allow_prefixes
    ):
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
        default=list(DEFAULT_ALLOWED_SCHEMES),
        help="Allowed URI scheme (repeatable, default: https)",
    )
    parser.add_argument(
        "--policy-file",
        default=None,
        help=(
            "Optional JSON policy file with "
            "allowed_schemes/blocked_schemes/allowed_prefixes"
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    allow_prefixes = tuple(args.allow_prefix)
    allow_schemes = tuple(args.allow_scheme)
    blocked_schemes = DEFAULT_BLOCKED_SCHEMES
    if args.policy_file:
        policy = load_policy_defaults(args.policy_file)
        if not allow_prefixes:
            allow_prefixes = policy.allowed_prefixes
        if args.allow_scheme == list(DEFAULT_ALLOWED_SCHEMES):
            allow_schemes = policy.allowed_schemes
        blocked_schemes = policy.blocked_schemes
    try:
        validate_untrusted_uri(
            args.uri,
            allow_prefixes=allow_prefixes,
            allowed_schemes=allow_schemes,
            blocked_schemes=blocked_schemes,
        )
    except ValueError as exc:
        print(f"[security-uri-check] FAIL: {exc}")
        return 1

    print("[security-uri-check] OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
