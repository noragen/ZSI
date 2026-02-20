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

    def test_detects_deep_xml_nesting(self):
        deep_xml = "<a><b><c><d><e/></d></c></b></a>"
        findings = run_security_scan_smoke(
            "https://example.internal/service",
            deep_xml,
            max_allowed_depth=4,
        )
        self.assertIn("deep_xml_nesting", findings)

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
