#!/usr/bin/env python
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from scripts.security_input_guard import validate_untrusted_uri


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


def makeTestSuite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(SecurityInputGuardTests)


if __name__ == "__main__":
    unittest.main(defaultTest="makeTestSuite")
