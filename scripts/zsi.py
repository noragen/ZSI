#!/usr/bin/env python3
"""Minimal DX CLI wrapper for compact ZSI commands."""

import sys

from scripts import zsi_call


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] not in ("call",):
        print(
            "usage: zsi call <wsdl> <operation> [key=value ...] "
            "[--service ...] [--port ...]"
        )
        return 2
    cmd = argv.pop(0)
    if cmd == "call":
        return zsi_call.main(argv)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
