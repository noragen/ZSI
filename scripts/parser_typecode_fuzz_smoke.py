#!/usr/bin/env python
"""Deterministic local parser/typecode fuzz-smoke checks.

This smoke targets robustness only:
- no unexpected crashes for adversarial parser/typecode inputs
- expected security findings are reported for known risky patterns
"""

from __future__ import annotations

import argparse
import random
import sys
from dataclasses import dataclass
from xml.parsers.expat import ExpatError

from ZSI import TC, EvaluateException, ParsedSoap, ParseException

try:
    from scripts.security_scan_smoke import run_security_scan_smoke
except ImportError:
    from security_scan_smoke import run_security_scan_smoke  # type: ignore


DEFAULT_SEED = 1337
DEFAULT_CASES = 24

_SAFE_URI = "https://schemas.example.internal/wsdl/service.wsdl"


@dataclass(frozen=True)
class FuzzCase:
    case_id: str
    uri: str
    xml_payload: str
    parse_mode: str = "soap_any"
    expected_security_findings: tuple[str, ...] = ()


def _soap_envelope(body_inner_xml: str) -> str:
    return (
        "<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/'>"
        "<soapenv:Body>"
        f"{body_inner_xml}"
        "</soapenv:Body>"
        "</soapenv:Envelope>"
    )


def _random_ascii_word(rng: random.Random, min_len: int = 4, max_len: int = 16) -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    size = rng.randint(min_len, max_len)
    return "".join(rng.choice(alphabet) for _ in range(size))


def _deep_nested_xml(depth: int) -> str:
    inner = "v"
    for _ in range(depth):
        inner = f"<n>{inner}</n>"
    return _soap_envelope(f"<Echo xmlns='urn:test'>{inner}</Echo>")


def _attribute_stress_xml(
    attr_count: int,
    attr_name_len: int,
    attr_value_len: int,
) -> str:
    name = "a" * attr_name_len
    value = "v" * attr_value_len
    attrs = " ".join(f"{name}{i}='{value}'" for i in range(attr_count))
    return _soap_envelope(f"<Echo xmlns='urn:test' {attrs}>ok</Echo>")


def _malformed_variant(rng: random.Random, xml_payload: str) -> str:
    # Deterministic local mutation set: truncate or corrupt close tag.
    choice = rng.randint(0, 1)
    if choice == 0:
        cut = max(1, len(xml_payload) // 3)
        return xml_payload[:-cut]
    return xml_payload.replace("</soapenv:Envelope>", "", 1)


def _build_case(rng: random.Random, index: int) -> FuzzCase:
    case_type = rng.choice(
        (
            "safe",
            "blocked_scheme",
            "credentials",
            "ssrf_localhost",
            "deep_xml",
            "attrs",
            "malformed",
            "typecode_int_mismatch",
        )
    )

    if case_type == "safe":
        value = _random_ascii_word(rng)
        return FuzzCase(
            case_id=f"case_{index:03d}_safe",
            uri=_SAFE_URI,
            xml_payload=_soap_envelope(f"<Echo xmlns='urn:test'>{value}</Echo>"),
        )

    if case_type == "blocked_scheme":
        value = _random_ascii_word(rng)
        return FuzzCase(
            case_id=f"case_{index:03d}_blocked_scheme",
            uri="file:///etc/passwd",
            xml_payload=_soap_envelope(f"<Echo xmlns='urn:test'>{value}</Echo>"),
            expected_security_findings=("blocked_uri_scheme",),
        )

    if case_type == "credentials":
        value = _random_ascii_word(rng)
        return FuzzCase(
            case_id=f"case_{index:03d}_credentials",
            uri="https://user:secret@example.internal/service",
            xml_payload=_soap_envelope(f"<Echo xmlns='urn:test'>{value}</Echo>"),
            expected_security_findings=("uri_embedded_credentials",),
        )

    if case_type == "ssrf_localhost":
        value = _random_ascii_word(rng)
        return FuzzCase(
            case_id=f"case_{index:03d}_ssrf_localhost",
            uri="http://localhost/service",
            xml_payload=_soap_envelope(f"<Echo xmlns='urn:test'>{value}</Echo>"),
            expected_security_findings=("ssrf_localhost",),
        )

    if case_type == "deep_xml":
        depth = rng.randint(18, 28)
        return FuzzCase(
            case_id=f"case_{index:03d}_deep_xml",
            uri=_SAFE_URI,
            xml_payload=_deep_nested_xml(depth),
            expected_security_findings=("deep_xml_nesting",),
        )

    if case_type == "attrs":
        return FuzzCase(
            case_id=f"case_{index:03d}_attrs",
            uri=_SAFE_URI,
            xml_payload=_attribute_stress_xml(
                attr_count=rng.randint(10, 14),
                attr_name_len=rng.randint(20, 30),
                attr_value_len=rng.randint(32, 48),
            ),
            expected_security_findings=(
                "excessive_attribute_count",
                "oversized_attribute_name",
                "oversized_attribute_value",
            ),
        )

    if case_type == "malformed":
        valid = _soap_envelope(
            f"<Echo xmlns='urn:test'>{_random_ascii_word(rng)}</Echo>"
        )
        return FuzzCase(
            case_id=f"case_{index:03d}_malformed",
            uri=_SAFE_URI,
            xml_payload=_malformed_variant(rng, valid),
            expected_security_findings=("malformed_soap_envelope",),
        )

    return FuzzCase(
        case_id=f"case_{index:03d}_typecode_int_mismatch",
        uri=_SAFE_URI,
        xml_payload=_soap_envelope("<Value xmlns='urn:test'>not-an-int</Value>"),
        parse_mode="soap_integer",
    )


def _exercise_parse(case: FuzzCase) -> tuple[bool, str | None]:
    try:
        parsed = ParsedSoap(case.xml_payload)
        if parsed.body_root is None:
            return True, None
        if case.parse_mode == "soap_integer":
            TC.Integer().parse(parsed.body_root, parsed)
        else:
            TC.Any().parse(parsed.body_root, parsed)
        return True, None
    except (ParseException, EvaluateException, ExpatError):
        return True, None
    except Exception as exc:
        return False, f"{exc.__class__.__name__}: {exc}"


def run_parser_typecode_fuzz_smoke(
    seed: int = DEFAULT_SEED,
    cases: int = DEFAULT_CASES,
) -> dict[str, object]:
    rng = random.Random(seed)
    results: list[dict[str, object]] = []
    unexpected_crashes: list[str] = []
    missing_expected_security: list[str] = []

    for index in range(cases):
        case = _build_case(rng, index)
        findings = run_security_scan_smoke(
            case.uri,
            case.xml_payload,
            max_allowed_depth=16,
            max_attributes_per_element=8,
            max_attribute_name_length=16,
            max_attribute_value_length=24,
            max_qname_length=48,
        )
        missing = [
            finding
            for finding in case.expected_security_findings
            if finding not in findings
        ]
        if missing:
            missing_expected_security.append(
                f"{case.case_id}: missing {', '.join(missing)}"
            )

        ok, crash_message = _exercise_parse(case)
        if not ok and crash_message is not None:
            unexpected_crashes.append(f"{case.case_id}: {crash_message}")

        results.append(
            {
                "case_id": case.case_id,
                "findings": tuple(findings),
                "missing_expected": tuple(missing),
                "parse_ok": ok,
            }
        )

    return {
        "seed": seed,
        "cases": cases,
        "results": tuple(results),
        "unexpected_crashes": tuple(unexpected_crashes),
        "missing_expected_security": tuple(missing_expected_security),
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run deterministic local parser/typecode fuzz-smoke checks"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help="Deterministic RNG seed",
    )
    parser.add_argument(
        "--cases",
        type=int,
        default=DEFAULT_CASES,
        help="Number of generated fuzz-smoke cases",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    summary = run_parser_typecode_fuzz_smoke(seed=args.seed, cases=args.cases)

    unexpected_crashes = summary["unexpected_crashes"]
    missing_expected = summary["missing_expected_security"]

    if unexpected_crashes or missing_expected:
        print("[parser-typecode-fuzz-smoke] FAIL")
        for item in unexpected_crashes:
            print(f" - unexpected_crash: {item}")
        for item in missing_expected:
            print(f" - missing_expected_security: {item}")
        return 1

    print("[parser-typecode-fuzz-smoke] OK")
    print(f"seed={summary['seed']} cases={summary['cases']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
