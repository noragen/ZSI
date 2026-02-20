#!/usr/bin/env python
"""Deterministic local smoke checks for common SOAP security pitfalls."""

from __future__ import annotations

import argparse
import io
import sys
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit

BLOCKED_URI_SCHEMES = {
    "data",
    "file",
    "ftp",
    "gopher",
    "jar",
    "javascript",
}

SOAP_ENVELOPE_NAMESPACES = {
    "http://schemas.xmlsoap.org/soap/envelope/",
    "http://www.w3.org/2003/05/soap-envelope",
}



def _local_name(tag: str) -> str:
    if tag.startswith("{") and "}" in tag:
        return tag.split("}", 1)[1]
    return tag



def _namespace(tag: str) -> str:
    if tag.startswith("{") and "}" in tag:
        return tag[1:].split("}", 1)[0]
    return ""



def _scan_uri(uri: str) -> list[str]:
    findings: list[str] = []
    parsed = urlsplit(uri)

    scheme = parsed.scheme.lower()
    if scheme in BLOCKED_URI_SCHEMES:
        findings.append("blocked_uri_scheme")

    if parsed.username is not None or parsed.password is not None:
        findings.append("uri_embedded_credentials")

    return findings



def _max_xml_depth(xml_payload: str) -> int:
    depth = 0
    max_depth = 0

    for event, _ in ET.iterparse(io.StringIO(xml_payload), events=("start", "end")):
        if event == "start":
            depth += 1
            if depth > max_depth:
                max_depth = depth
        else:
            depth -= 1

    return max_depth



def _is_malformed_soap_envelope(xml_payload: str) -> bool:
    try:
        root = ET.fromstring(xml_payload)
    except ET.ParseError:
        return True

    root_name = _local_name(root.tag)
    root_ns = _namespace(root.tag)

    if root_name != "Envelope" or root_ns not in SOAP_ENVELOPE_NAMESPACES:
        return True

    body_tag = f"{{{root_ns}}}Body"
    return root.find(body_tag) is None



def run_security_scan_smoke(
    uri: str, xml_payload: str, max_allowed_depth: int = 32
) -> list[str]:
    """Return deterministic finding identifiers for local security smoke checks."""
    findings: list[str] = []

    findings.extend(_scan_uri(uri))

    try:
        depth = _max_xml_depth(xml_payload)
    except ET.ParseError:
        findings.append("malformed_soap_envelope")
    else:
        if depth > max_allowed_depth:
            findings.append("deep_xml_nesting")

        if _is_malformed_soap_envelope(xml_payload):
            findings.append("malformed_soap_envelope")

    # Preserve order while removing duplicates.
    return list(dict.fromkeys(findings))



def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run deterministic local security smoke checks for SOAP inputs"
    )
    parser.add_argument("--uri", required=True, help="Untrusted URI candidate")
    parser.add_argument(
        "--xml-file",
        required=True,
        help="Path to SOAP XML payload used for local checks",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=32,
        help="Maximum allowed XML nesting depth before reporting deep_xml_nesting",
    )
    return parser.parse_args(argv)



def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)

    with open(args.xml_file, encoding="utf-8") as handle:
        xml_payload = handle.read()

    findings = run_security_scan_smoke(
        args.uri,
        xml_payload,
        max_allowed_depth=args.max_depth,
    )

    if findings:
        print("[security-scan-smoke] FAIL")
        for finding in findings:
            print(f" - {finding}")
        return 1

    print("[security-scan-smoke] OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
