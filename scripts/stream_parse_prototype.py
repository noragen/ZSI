#!/usr/bin/env python
"""CLI for streaming SOAP envelope scan prototype."""

from __future__ import annotations

import argparse
import json

from ZSI.stream_parse import stream_scan_envelope


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xml-file", required=True, help="Path to XML/SOAP payload")
    args = parser.parse_args()

    with open(args.xml_file, "rb") as fh:
        result = stream_scan_envelope(fh.read())
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
