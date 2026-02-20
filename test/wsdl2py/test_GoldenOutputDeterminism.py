#!/usr/bin/env python

import hashlib
import os
import tempfile
import unittest

from ZSI.generate import commands


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        h.update(fh.read())
    return h.hexdigest()


class GoldenOutputDeterminismTests(unittest.TestCase):
    def test_wsdl2py_rewrite_is_deterministic_for_same_inputs(self):
        wsdl = os.path.join("test", "wsdl2py", "wsdl", "NoMessagePart.wsdl")
        with tempfile.TemporaryDirectory() as td:
            files1 = commands.wsdl2py(["--output-dir", td, wsdl])
            hashes1 = {}
            for p in files1:
                full = p if os.path.isabs(p) else os.path.join(td, p)
                hashes1[os.path.basename(full)] = _sha256(full)

            files2 = commands.wsdl2py(["--output-dir", td, wsdl])
            hashes2 = {}
            for p in files2:
                full = p if os.path.isabs(p) else os.path.join(td, p)
                hashes2[os.path.basename(full)] = _sha256(full)

            self.assertEqual(hashes1, hashes2)



def makeTestSuite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(GoldenOutputDeterminismTests)


def local():
    return makeTestSuite()


if __name__ == "__main__":
    unittest.main(defaultTest="makeTestSuite")
