#!/usr/bin/env python
import unittest

from ZSI.client import _Binding


class _FakeConnection:
    def __init__(self):
        self.headers = []
        self.request = None
        self.body = None

    def putrequest(self, method, uri):
        self.request = (method, uri)

    def putheader(self, key, value):
        self.headers.append((key, value))

    def endheaders(self):
        return None

    def send(self, body):
        self.body = body


class TransportModernizationTests(unittest.TestCase):
    def test_timeout_shortcut_maps_to_transdict(self):
        b = _Binding(url="http://example.invalid/service", timeout=5)
        self.assertEqual(5, b.transdict.get("timeout"))

    def test_soap12_uses_application_soap_xml_without_soapaction_header(self):
        b = _Binding(url="http://example.invalid/service", soapaction="urn:echo", soap_version="1.2")
        b.h = _FakeConnection()
        b.boundary = ""
        b._Binding__addcookies = lambda: None
        b.SendSOAPData("<Envelope/>", b.url, b.soapaction)
        headers = dict(b.h.headers)
        self.assertIn("Content-Type", headers)
        self.assertIn("application/soap+xml", headers["Content-Type"])
        self.assertNotIn("SOAPAction", headers)


def makeTestSuite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(TransportModernizationTests)


if __name__ == "__main__":
    unittest.main(defaultTest="makeTestSuite")
