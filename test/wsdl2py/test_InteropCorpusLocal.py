#!/usr/bin/env python

import os
import tempfile
import unittest

from ZSI.generate import commands


INTEROP_WSDLS = (
    "InteropTest.wsdl",
    "InteropTestB.wsdl",
    "echoHeaderBindings.wsdl",
)


class InteropCorpusLocalTests(unittest.TestCase):
    def test_local_interop_wsdl_corpus_generates_stubs(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        interop_dir = os.path.join(root, "interop")

        with tempfile.TemporaryDirectory() as td:
            for wsdl_name in INTEROP_WSDLS:
                with self.subTest(wsdl=wsdl_name):
                    wsdl_path = os.path.join(interop_dir, wsdl_name)
                    files = commands.wsdl2py(["--compat", "--output-dir", td, wsdl_path])
                    self.assertTrue(files, "expected generated file list")
                    self.assertTrue(any(name.endswith("_types.py") for name in files))
                    for generated in files:
                        full = generated if os.path.isabs(generated) else os.path.join(td, generated)
                        self.assertTrue(os.path.exists(full), f"missing generated file: {full}")


def makeTestSuite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(InteropCorpusLocalTests)


def local():
    return makeTestSuite()


if __name__ == "__main__":
    unittest.main(defaultTest="makeTestSuite")
