#!/usr/bin/env python
import os
import sys
import tempfile
import json
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from scripts.security_input_guard import validate_untrusted_uri
from scripts.security_policy_defaults import load_policy_defaults


class SecurityInputGuardTests(unittest.TestCase):
    def test_allows_https_with_trusted_prefix(self):
        validate_untrusted_uri(
            "https://schemas.example.internal/wsdl/service.wsdl",
            allow_prefixes=("https://schemas.example.internal/",),
        )

    def test_rejects_file_scheme(self):
        with self.assertRaises(ValueError):
            validate_untrusted_uri("file:///etc/passwd")

    def test_rejects_embedded_credentials(self):
        with self.assertRaises(ValueError):
            validate_untrusted_uri("https://user:secret@example.internal/wsdl")

    def test_rejects_control_chars(self):
        with self.assertRaises(ValueError):
            validate_untrusted_uri("https://example.internal/wsdl\n")

    def test_rejects_non_absolute_uri(self):
        with self.assertRaises(ValueError):
            validate_untrusted_uri("/local/path.wsdl")

    def test_rejects_untrusted_prefix(self):
        with self.assertRaises(ValueError):
            validate_untrusted_uri(
                "https://evil.example/wsdl",
                allow_prefixes=("https://schemas.example.internal/",),
            )

    def test_rejects_localhost_hostnames(self):
        with self.assertRaises(ValueError):
            validate_untrusted_uri("https://localhost/wsdl")
        with self.assertRaises(ValueError):
            validate_untrusted_uri("https://api.localhost/wsdl")

    def test_rejects_loopback_private_and_metadata_ips(self):
        blocked = (
            "https://127.0.0.1/wsdl",
            "https://10.1.2.3/wsdl",
            "https://172.16.8.9/wsdl",
            "https://192.168.2.2/wsdl",
            "https://169.254.169.254/wsdl",
        )
        for uri in blocked:
            with self.subTest(uri=uri):
                with self.assertRaises(ValueError):
                    validate_untrusted_uri(uri)

    def test_policy_file_loader(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "policy.json")
            with open(p, "w", encoding="utf-8") as fh:
                json.dump(
                    {
                        "allowed_schemes": ["https", "http"],
                        "blocked_schemes": ["file", "data"],
                        "allowed_prefixes": ["http://safe.local/"],
                    },
                    fh,
                )
            policy = load_policy_defaults(p)
            self.assertEqual(("https", "http"), policy.allowed_schemes)
            self.assertIn("file", policy.blocked_schemes)
            self.assertEqual(("http://safe.local/",), policy.allowed_prefixes)

    def test_policy_values_can_drive_validation(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "policy.json")
            with open(p, "w", encoding="utf-8") as fh:
                json.dump(
                    {
                        "allowed_schemes": ["http"],
                        "blocked_schemes": ["https"],
                        "allowed_prefixes": ["http://safe.local/"],
                    },
                    fh,
                )
            policy = load_policy_defaults(p)
            validate_untrusted_uri(
                "http://safe.local/service.wsdl",
                allow_prefixes=policy.allowed_prefixes,
                allowed_schemes=policy.allowed_schemes,
                blocked_schemes=policy.blocked_schemes,
            )
            with self.assertRaises(ValueError):
                validate_untrusted_uri(
                    "https://safe.local/service.wsdl",
                    allow_prefixes=policy.allowed_prefixes,
                    allowed_schemes=policy.allowed_schemes,
                    blocked_schemes=policy.blocked_schemes,
                )


def makeTestSuite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(SecurityInputGuardTests)


if __name__ == "__main__":
    unittest.main(defaultTest="makeTestSuite")
