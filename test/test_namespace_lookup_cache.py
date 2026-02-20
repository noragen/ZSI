#!/usr/bin/env python
import unittest
from xml.dom import minidom

import ZSI


class NamespaceLookupCacheTests(unittest.TestCase):
    def test_resolve_prefix_populates_cache(self):
        doc = minidom.parseString('<a xmlns:x="urn:test"><b><x:c/></b></a>')
        c = doc.getElementsByTagName("x:c")[0]
        b = c.parentNode

        # call twice to hit cache path on second lookup
        ns1 = ZSI._resolve_prefix(b, "x")
        ns2 = ZSI._resolve_prefix(b, "x")
        self.assertEqual("urn:test", ns1)
        self.assertEqual(ns1, ns2)
        self.assertIn((id(b), "x"), ZSI._resolve_prefix.cache)


def makeTestSuite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(NamespaceLookupCacheTests)


if __name__ == "__main__":
    unittest.main(defaultTest="makeTestSuite")
