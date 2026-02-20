#!/usr/bin/env python
import unittest

from ZSI.stream_parse import stream_scan_envelope


SOAP = """\
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
  <soapenv:Header/>
  <soapenv:Body>
    <Echo xmlns="urn:test"><Msg>hello</Msg></Echo>
  </soapenv:Body>
</soapenv:Envelope>
"""


class StreamParsePrototypeTests(unittest.TestCase):
    def test_stream_scan_finds_body_root(self):
        out = stream_scan_envelope(SOAP)
        self.assertEqual("{urn:test}Echo", out["body_root_tag"])
        self.assertGreater(out["element_count"], 0)
        self.assertGreater(out["max_depth"], 0)


def makeTestSuite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(StreamParsePrototypeTests)


if __name__ == "__main__":
    unittest.main(defaultTest="makeTestSuite")
