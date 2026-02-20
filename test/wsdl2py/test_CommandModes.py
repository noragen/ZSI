#!/usr/bin/env python

import os
import tempfile
import unittest
from unittest import mock

from ZSI.generate import commands


class _FakeReader:
    def loadFromFile(self, location):
        return object()


class _FakeWSDL:
    def __init__(self, types_count=1, services_count=1):
        self.types = {"urn:test": object()} if types_count else {}
        self.services = {"svc": object()} if services_count else {}
        self.location = "fake.wsdl"


class _FakeSchema:
    def __init__(self, tns="urn:test"):
        self._tns = tns

    def getTargetNamespace(self):
        return self._tns


class CommandModesTests(unittest.TestCase):
    def test_strict_compat_conflict_raises(self):
        with self.assertRaises(ValueError):
            commands.wsdl2py(["--strict-schema", "--compat", "dummy.wsdl"])

    def test_validate_wsdl_strict_fails_for_empty_services(self):
        with self.assertRaises(ValueError):
            commands._validate_wsdl_strict(_FakeWSDL(types_count=1, services_count=0), schema_mode=False)

    def test_validate_schema_strict_requires_target_namespace(self):
        with self.assertRaises(ValueError):
            commands._validate_wsdl_strict(_FakeSchema(tns=""), schema_mode=True)

    def test_compat_mode_tolerates_dispatch_failure(self):
        with tempfile.TemporaryDirectory() as td:
            wsdl_path = os.path.join(td, "fake.wsdl")
            with open(wsdl_path, "w", encoding="utf-8") as fh:
                fh.write("<definitions/>")

            with mock.patch.object(commands.WSDLTools, "WSDLReader", return_value=_FakeReader()):
                with mock.patch.object(commands, "_wsdl2py", return_value=["types.py"]):
                    with mock.patch.object(commands, "_wsdl2dispatch", side_effect=RuntimeError("dispatch boom")):
                        files = commands.wsdl2py(["--compat", wsdl_path])
            self.assertEqual(["types.py"], files)



def makeTestSuite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(CommandModesTests)


def local():
    return makeTestSuite()


if __name__ == "__main__":
    unittest.main(defaultTest="makeTestSuite")
