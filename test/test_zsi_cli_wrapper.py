#!/usr/bin/env python
import unittest
from unittest import mock

import scripts.zsi as zsi_cli


class ZSIWrapperCLITests(unittest.TestCase):
    def test_call_subcommand_dispatches(self):
        with mock.patch("scripts.zsi_call.main", return_value=0) as call_main:
            rc = zsi_cli.main(["call", "wsdl", "Op", "a=1"])
        self.assertEqual(0, rc)
        call_main.assert_called_once()


def makeTestSuite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(ZSIWrapperCLITests)


if __name__ == "__main__":
    unittest.main(defaultTest="makeTestSuite")
