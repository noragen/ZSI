#!/usr/bin/env python
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from scripts.security_scan_smoke import run_security_scan_smoke

VALID_SOAP = """\
<soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\">
  <soapenv:Body>
    <Echo xmlns=\"urn:test\">hello</Echo>
  </soapenv:Body>
</soapenv:Envelope>
"""


class SecurityScanSmokeTests(unittest.TestCase):
    def test_detects_blocked_uri_scheme(self):
        findings = run_security_scan_smoke("file:///etc/passwd", VALID_SOAP)
        self.assertIn("blocked_uri_scheme", findings)

    def test_detects_credentials_in_uri(self):
        findings = run_security_scan_smoke(
            "https://user:secret@example.internal/service",
            VALID_SOAP,
        )
        self.assertIn("uri_embedded_credentials", findings)

    def test_detects_ssrf_localhost(self):
        findings = run_security_scan_smoke("http://localhost/service", VALID_SOAP)
        self.assertIn("ssrf_localhost", findings)

    def test_detects_ssrf_loopback_ip(self):
        findings = run_security_scan_smoke("http://127.0.0.1/service", VALID_SOAP)
        self.assertIn("ssrf_loopback_ip", findings)

    def test_detects_ssrf_metadata_ip(self):
        findings = run_security_scan_smoke(
            "http://169.254.169.254/latest/meta-data/",
            VALID_SOAP,
        )
        self.assertIn("ssrf_cloud_metadata_ip", findings)

    def test_detects_ssrf_private_ip_ranges(self):
        uris = [
            "http://10.10.10.10/service",
            "http://172.16.1.2/service",
            "http://192.168.20.5/service",
        ]
        for uri in uris:
            with self.subTest(uri=uri):
                findings = run_security_scan_smoke(uri, VALID_SOAP)
                self.assertIn("ssrf_private_ip", findings)

    def test_detects_deep_xml_nesting(self):
        deep_xml = "<a><b><c><d><e/></d></c></b></a>"
        findings = run_security_scan_smoke(
            "https://example.internal/service",
            deep_xml,
            max_allowed_depth=4,
        )
        self.assertIn("deep_xml_nesting", findings)

    def test_detects_oversized_payload(self):
        large_body = "x" * 256
        payload = (
            "<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/'>"
            "<soapenv:Body><Echo xmlns='urn:test'>"
            f"{large_body}"
            "</Echo></soapenv:Body></soapenv:Envelope>"
        )
        findings = run_security_scan_smoke(
            "https://example.internal/service",
            payload,
            max_xml_payload_bytes=128,
        )
        self.assertIn("oversized_xml_payload", findings)

    def test_detects_excessive_attribute_count(self):
        attrs = " ".join(f"a{i}='v'" for i in range(6))
        payload = (
            "<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/'>"
            f"<soapenv:Body><Echo xmlns='urn:test' {attrs}>ok</Echo></soapenv:Body>"
            "</soapenv:Envelope>"
        )
        findings = run_security_scan_smoke(
            "https://example.internal/service",
            payload,
            max_attributes_per_element=5,
        )
        self.assertIn("excessive_attribute_count", findings)

    def test_detects_oversized_attribute_value(self):
        long_value = "v" * 64
        payload = (
            "<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/'>"
            "<soapenv:Body>"
            f"<Echo xmlns='urn:test' a='{long_value}'>ok</Echo>"
            "</soapenv:Body></soapenv:Envelope>"
        )
        findings = run_security_scan_smoke(
            "https://example.internal/service",
            payload,
            max_attribute_value_length=16,
        )
        self.assertIn("oversized_attribute_value", findings)

    def test_detects_oversized_attribute_name_and_qname(self):
        long_name = "A" * 40
        payload = (
            "<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/'>"
            "<soapenv:Body>"
            f"<{long_name} xmlns='urn:test' {long_name}='x'>ok</{long_name}>"
            "</soapenv:Body></soapenv:Envelope>"
        )
        findings = run_security_scan_smoke(
            "https://example.internal/service",
            payload,
            max_qname_length=16,
            max_attribute_name_length=16,
        )
        self.assertIn("oversized_qname", findings)
        self.assertIn("oversized_attribute_name", findings)

    def test_detects_malformed_soap_envelope(self):
        malformed = "<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/'><soapenv:Body>"
        findings = run_security_scan_smoke("https://example.internal/service", malformed)
        self.assertIn("malformed_soap_envelope", findings)

    def test_accepts_safe_inputs(self):
        findings = run_security_scan_smoke("https://example.internal/service", VALID_SOAP)
        self.assertEqual([], findings)


def makeTestSuite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(SecurityScanSmokeTests)


if __name__ == "__main__":
    unittest.main(defaultTest="makeTestSuite")
