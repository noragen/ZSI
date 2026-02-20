#!/usr/bin/env python
import unittest

from scripts.zsi_call import _parse_kv


class ZSICallCLITests(unittest.TestCase):
    def test_parse_kv_literal_eval(self):
        payload = _parse_kv(["a=1", "b=True", "c='x'"])
        self.assertEqual(1, payload["a"])
        self.assertEqual(True, payload["b"])
        self.assertEqual("x", payload["c"])


def makeTestSuite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(ZSICallCLITests)


if __name__ == "__main__":
    unittest.main(defaultTest="makeTestSuite")
