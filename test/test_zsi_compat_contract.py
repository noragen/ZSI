#!/usr/bin/env python
import os
import tempfile
import unittest

import ZSI
from ZSI.generate import commands


class ZSICompatContractTests(unittest.TestCase):
    def test_legacy_public_entrypoints_still_exist(self):
        required = [
            "ParsedSoap",
            "SoapWriter",
            "Fault",
            "FaultException",
            "FaultFromException",
            "FaultFromZSIException",
            "TC",
            "_get_postvalue_from_absoluteURI",
        ]
        for name in required:
            with self.subTest(symbol=name):
                self.assertTrue(hasattr(ZSI, name), f"missing compatibility symbol: {name}")

    def test_wsdl2py_default_path_remains_usable(self):
        wsdl = os.path.join("test", "wsdl2py", "wsdl", "NoMessagePart.wsdl")
        with tempfile.TemporaryDirectory() as td:
            files = commands.wsdl2py(["--output-dir", td, wsdl])
            self.assertTrue(any(path.endswith("_client.py") for path in files))
            self.assertTrue(any(path.endswith("_types.py") for path in files))
            for path in files:
                full = path if os.path.isabs(path) else os.path.join(td, path)
                self.assertTrue(os.path.exists(full), f"missing generated file: {full}")


def makeTestSuite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(ZSICompatContractTests)


if __name__ == "__main__":
    unittest.main(defaultTest="makeTestSuite")
