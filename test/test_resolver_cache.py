#!/usr/bin/env python
import io
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ZSI import TC
from ZSI.resolvers import ClearNetworkResolverCache, NetworkResolver


class _FakeInfo:
    def get(self, name, default=None):
        if name.lower() == "content-transfer-encoding":
            return "binary"
        return default

    def get_content_charset(self):
        return None


class _FakeSource:
    def __init__(self, body: bytes):
        self._body = body

    def info(self):
        return _FakeInfo()

    def read(self):
        return self._body


class _FakeReader:
    def fromStream(self, stream):
        return io.StringIO(stream.read())


class _FakePS:
    readerclass = _FakeReader


class ResolverCacheTests(unittest.TestCase):
    def setUp(self):
        ClearNetworkResolverCache()

    def test_opaque_uses_url_hash_cache(self):
        resolver = NetworkResolver(prefix=["https://example.internal/"])
        uri = "https://example.internal/schema.xsd"
        opener = mock.Mock(return_value=_FakeSource(b"abc"))

        with mock.patch("urllib.request.urlopen", opener):
            a = resolver.Opaque(uri, TC.Any(), _FakePS())
            b = resolver.Opaque(uri, TC.Any(), _FakePS())

        self.assertEqual(a, b)
        self.assertEqual(opener.call_count, 1)


def makeTestSuite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(ResolverCacheTests)


if __name__ == "__main__":
    unittest.main(defaultTest="makeTestSuite")
