#!/usr/bin/env python
"""Central defaults for URI security policy checks."""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_ALLOWED_SCHEMES: tuple[str, ...] = ("https",)
DEFAULT_BLOCKED_SCHEMES: frozenset[str] = frozenset(
    {
        "file",
        "ftp",
        "gopher",
        "data",
        "javascript",
        "jar",
    }
)
DEFAULT_ALLOWED_PREFIXES: tuple[str, ...] = ()


@dataclass(frozen=True)
class URISecurityPolicyDefaults:
    """Container for default URI validation policy values."""

    allowed_schemes: tuple[str, ...] = DEFAULT_ALLOWED_SCHEMES
    blocked_schemes: frozenset[str] = DEFAULT_BLOCKED_SCHEMES
    allowed_prefixes: tuple[str, ...] = DEFAULT_ALLOWED_PREFIXES


def normalize_schemes(values: tuple[str, ...]) -> tuple[str, ...]:
    """Return a lower-cased scheme tuple while preserving order."""
    return tuple(s.lower() for s in values)

