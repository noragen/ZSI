#!/usr/bin/env python
import unittest
import test_t4
import test_callhome
import test_zsi

def makeTestSuite():
    modules = (test_t4, test_callhome) + test_zsi.TEST_MODULES
    return unittest.TestSuite([module.makeTestSuite() for module in modules])

def main():
    unittest.main(defaultTest="makeTestSuite")

if __name__ == "__main__" :
    main()
