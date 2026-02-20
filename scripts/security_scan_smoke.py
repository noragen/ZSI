#!/usr/bin/env python
"""Deterministic local smoke checks for common SOAP security pitfalls."""

from __future__ import annotations

import argparse
import ipaddress
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

DEFAULT_MAX_XML_PAYLOAD_BYTES = 128 * 1024
DEFAULT_MAX_ATTRIBUTES_PER_ELEMENT = 64
DEFAULT_MAX_ATTRIBUTE_NAME_LENGTH = 128
DEFAULT_MAX_ATTRIBUTE_VALUE_LENGTH = 4096
DEFAULT_MAX_QNAME_LENGTH = 256


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

    hostname = (parsed.hostname or "").strip().lower()
    if hostname:
        if hostname == "localhost" or hostname.endswith(".localhost"):
            findings.append("ssrf_localhost")
        else:
            try:
                host_ip = ipaddress.ip_address(hostname)
            except ValueError:
                host_ip = None

            if host_ip is not None:
                if host_ip.is_loopback:
                    findings.append("ssrf_loopback_ip")
                if host_ip == ipaddress.ip_address("169.254.169.254"):
                    findings.append("ssrf_cloud_metadata_ip")
                if host_ip.is_private:
                    findings.append("ssrf_private_ip")

    return findings


def _max_xml_depth_from_root(root: ET.Element) -> int:
    max_depth = 0
    stack: list[tuple[ET.Element, int]] = [(root, 1)]

    while stack:
        node, depth = stack.pop()
        if depth > max_depth:
            max_depth = depth
        for child in list(node):
            stack.append((child, depth + 1))

    return max_depth


def _is_malformed_soap_envelope_root(root: ET.Element) -> bool:
    root_name = _local_name(root.tag)
    root_ns = _namespace(root.tag)

    if root_name != "Envelope" or root_ns not in SOAP_ENVELOPE_NAMESPACES:
        return True

    body_tag = f"{{{root_ns}}}Body"
    return root.find(body_tag) is None


def _scan_xml_extremes(
    root: ET.Element,
    max_attributes_per_element: int,
    max_attribute_name_length: int,
    max_attribute_value_length: int,
    max_qname_length: int,
) -> list[str]:
    findings: list[str] = []

    for element in root.iter():
        element_local_name = _local_name(element.tag)
        if len(element_local_name) > max_qname_length:
            findings.append("oversized_qname")

        if len(element.attrib) > max_attributes_per_element:
            findings.append("excessive_attribute_count")

        for raw_attr_name, raw_attr_value in element.attrib.items():
            attr_name = _local_name(raw_attr_name)
            attr_value = str(raw_attr_value)

            if len(attr_name) > max_qname_length:
                findings.append("oversized_qname")
            if len(attr_name) > max_attribute_name_length:
                findings.append("oversized_attribute_name")
            if len(attr_value) > max_attribute_value_length:
                findings.append("oversized_attribute_value")

    return findings


def run_security_scan_smoke(
    uri: str,
    xml_payload: str,
    max_allowed_depth: int = 32,
    max_xml_payload_bytes: int = DEFAULT_MAX_XML_PAYLOAD_BYTES,
    max_attributes_per_element: int = DEFAULT_MAX_ATTRIBUTES_PER_ELEMENT,
    max_attribute_name_length: int = DEFAULT_MAX_ATTRIBUTE_NAME_LENGTH,
    max_attribute_value_length: int = DEFAULT_MAX_ATTRIBUTE_VALUE_LENGTH,
    max_qname_length: int = DEFAULT_MAX_QNAME_LENGTH,
) -> list[str]:
    """Return deterministic finding identifiers for local security smoke checks."""
    findings: list[str] = []

    findings.extend(_scan_uri(uri))

    if len(xml_payload.encode("utf-8")) > max_xml_payload_bytes:
        findings.append("oversized_xml_payload")

    try:
        root = ET.fromstring(xml_payload)
    except ET.ParseError:
        findings.append("malformed_soap_envelope")
    else:
        depth = _max_xml_depth_from_root(root)
        if depth > max_allowed_depth:
            findings.append("deep_xml_nesting")

        if _is_malformed_soap_envelope_root(root):
            findings.append("malformed_soap_envelope")

        findings.extend(
            _scan_xml_extremes(
                root,
                max_attributes_per_element=max_attributes_per_element,
                max_attribute_name_length=max_attribute_name_length,
                max_attribute_value_length=max_attribute_value_length,
                max_qname_length=max_qname_length,
            )
        )

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
    parser.add_argument(
        "--max-payload-bytes",
        type=int,
        default=DEFAULT_MAX_XML_PAYLOAD_BYTES,
        help="Maximum payload size in bytes before reporting oversized_xml_payload",
    )
    parser.add_argument(
        "--max-attributes-per-element",
        type=int,
        default=DEFAULT_MAX_ATTRIBUTES_PER_ELEMENT,
        help=(
            "Maximum attributes per XML element before reporting "
            "excessive_attribute_count"
        ),
    )
    parser.add_argument(
        "--max-attribute-name-length",
        type=int,
        default=DEFAULT_MAX_ATTRIBUTE_NAME_LENGTH,
        help="Maximum attribute name length before reporting oversized_attribute_name",
    )
    parser.add_argument(
        "--max-attribute-value-length",
        type=int,
        default=DEFAULT_MAX_ATTRIBUTE_VALUE_LENGTH,
        help=(
            "Maximum attribute value length before reporting "
            "oversized_attribute_value"
        ),
    )
    parser.add_argument(
        "--max-qname-length",
        type=int,
        default=DEFAULT_MAX_QNAME_LENGTH,
        help="Maximum XML QName length before reporting oversized_qname",
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
        max_xml_payload_bytes=args.max_payload_bytes,
        max_attributes_per_element=args.max_attributes_per_element,
        max_attribute_name_length=args.max_attribute_name_length,
        max_attribute_value_length=args.max_attribute_value_length,
        max_qname_length=args.max_qname_length,
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
