#!/usr/bin/env python
"""Central defaults for URI security policy checks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

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


def load_policy_defaults(path: str | Path) -> URISecurityPolicyDefaults:
    """Load URI security policy defaults from JSON file."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))

    allowed_schemes = tuple(payload.get("allowed_schemes", DEFAULT_ALLOWED_SCHEMES))
    blocked_schemes = frozenset(
        payload.get("blocked_schemes", tuple(DEFAULT_BLOCKED_SCHEMES))
    )
    allowed_prefixes = tuple(payload.get("allowed_prefixes", DEFAULT_ALLOWED_PREFIXES))

    return URISecurityPolicyDefaults(
        allowed_schemes=normalize_schemes(allowed_schemes),
        blocked_schemes=frozenset(s.lower() for s in blocked_schemes),
        allowed_prefixes=allowed_prefixes,
    )
