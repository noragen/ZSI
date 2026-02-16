#!/usr/bin/env python

import os
import unittest

def load_tests_from_test_case(test_case, method_prefix="test"):
    loader = unittest.TestLoader()
    loader.testMethodPrefix = method_prefix
    return loader.loadTestsFromTestCase(test_case)

from ZSI import version
from ZSI.wstools.logging import gridLog

os.environ['GRIDLOG_ON'] = '1'
os.environ['GRIDLOG_DEST'] = "gridlog-udp://netlogger.lbl.gov:15100"

class TestCase(unittest.TestCase):
    def ping(self):
        gridLog(event="zsi.test.test_callhome.ping", zsi="v%d.%d.%d" % version.Version,
            prog="test_callhome.py")

def makeTestSuite():
    suite = unittest.TestSuite()
    suite.addTest(load_tests_from_test_case(TestCase, "ping"))
    return suite

def main():
    unittest.main(defaultTest="makeTestSuite")

if __name__ == '__main__':
    main()


