#!/usr/bin/env python

import os
import tempfile
import unittest
from unittest import mock

from ZSI.generate import commands


class _FakeReader:
    def loadFromFile(self, location):
        return object()


class PluginHooksTests(unittest.TestCase):
    def test_plugin_hooks_are_invoked(self):
        with tempfile.TemporaryDirectory() as td:
            wsdl_path = os.path.join(td, "fake.wsdl")
            plugin_path = os.path.join(td, "plugin.py")
            events_path = os.path.join(td, "events.txt")
            plugin_code = f"""
from pathlib import Path
EVENTS_FILE = Path(r\"{events_path}\")

def _push(name):
    with EVENTS_FILE.open("a", encoding="utf-8") as fh:
        fh.write(name + "\\n")

def on_options(options):
    _push("on_options")

def on_wsdl_loaded(options, wsdl):
    _push("on_wsdl_loaded")

def before_generate(options, wsdl):
    _push("before_generate")

def after_generate(options, wsdl, files):
    _push("after_generate")
"""
            with open(wsdl_path, "w", encoding="utf-8") as fh:
                fh.write("<definitions/>")
            with open(plugin_path, "w", encoding="utf-8") as fh:
                fh.write(plugin_code)

            with mock.patch.object(commands.WSDLTools, "WSDLReader", return_value=_FakeReader()):
                with mock.patch.object(commands, "_wsdl2py", return_value=["types.py"]):
                    with mock.patch.object(commands, "_wsdl2dispatch", return_value="server.py"):
                        files = commands.wsdl2py(["--plugin", plugin_path, wsdl_path])

            self.assertEqual(["types.py", "server.py"], files)
            with open(events_path, encoding="utf-8") as fh:
                events = [line.strip() for line in fh if line.strip()]
            self.assertEqual(["on_options", "on_wsdl_loaded", "before_generate", "after_generate"], events)


def makeTestSuite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(PluginHooksTests)


def local():
    return makeTestSuite()


if __name__ == "__main__":
    unittest.main(defaultTest="makeTestSuite")
