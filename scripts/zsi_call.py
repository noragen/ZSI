#!/usr/bin/env python
"""Compact one-liner SOAP call helper for ZSI ServiceProxy."""

from __future__ import annotations

import argparse
import ast
import json

from ZSI.ServiceProxy import ServiceProxy


def _parse_value(value: str):
    try:
        return ast.literal_eval(value)
    except Exception:
        return value


def _parse_kv(items):
    out = {}
    for item in items:
        if "=" not in item:
            raise ValueError('arguments must be key=value, got "%s"' % item)
        key, value = item.split("=", 1)
        out[key] = _parse_value(value)
    return out


def _build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wsdl", help="WSDL URL/path")
    parser.add_argument("operation", help="Operation name")
    parser.add_argument("args", nargs="*", help="Operation arguments as key=value")
    parser.add_argument("--service", default=None, help="Optional service name")
    parser.add_argument("--port", default=None, help="Optional port name")
    parser.add_argument("--url", default=None, help="Override endpoint URL")
    parser.add_argument(
        "--asdict",
        action="store_true",
        default=False,
        help="Return dict-like structures when possible",
    )
    return parser


def main(argv=None):
    parser = _build_parser()
    ns = parser.parse_args(argv)
    kwargs = _parse_kv(ns.args)

    proxy = ServiceProxy(ns.wsdl, url=ns.url, service=ns.service, port=ns.port, asdict=ns.asdict)
    bound = proxy.bind(service=ns.service, port=ns.port)
    result = getattr(bound, ns.operation)(**kwargs)

    try:
        print(json.dumps(result, default=lambda o: getattr(o, "__dict__", str(o)), indent=2))
    except Exception:
        print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
