#!/usr/bin/env python
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from scripts.parser_typecode_fuzz_smoke import run_parser_typecode_fuzz_smoke


class ParserTypecodeFuzzSmokeTests(unittest.TestCase):
    def test_deterministic_for_same_seed(self):
        first = run_parser_typecode_fuzz_smoke(seed=2026, cases=18)
        second = run_parser_typecode_fuzz_smoke(seed=2026, cases=18)
        self.assertEqual(first["results"], second["results"])
        self.assertEqual(first["unexpected_crashes"], second["unexpected_crashes"])
        self.assertEqual(
            first["missing_expected_security"],
            second["missing_expected_security"],
        )

    def test_no_unexpected_crash_and_expected_security_findings_present(self):
        result = run_parser_typecode_fuzz_smoke(seed=1337, cases=24)
        self.assertEqual((), result["unexpected_crashes"])
        self.assertEqual((), result["missing_expected_security"])


def makeTestSuite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(
        ParserTypecodeFuzzSmokeTests
    )


if __name__ == "__main__":
    unittest.main(defaultTest="makeTestSuite")
