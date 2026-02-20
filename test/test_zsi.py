#!/usr/bin/env python
import unittest
import test_t1
import test_t2
import test_t3
import test_t5
import test_t6
import test_t7
import test_t8
import test_t9
import test_union
import test_list
import test_TCtimes
import test_URI
import test_rfc2617
import test_QName
import test_AnyType
import test_security_input_guard
import test_security_scan_smoke

TEST_MODULES = (
    test_t1,
    test_t2,
    test_t3,
    test_t5,
    test_t6,
    test_t7,
    test_t8,
    test_t9,
    test_union,
    test_list,
    test_TCtimes,
    test_URI,
    test_rfc2617,
    test_QName,
    test_AnyType,
    test_security_input_guard,
    test_security_scan_smoke,
)

def makeTestSuite():
    return unittest.TestSuite([module.makeTestSuite() for module in TEST_MODULES])

def main():
    unittest.main(defaultTest="makeTestSuite")

if __name__ == "__main__":
    main()

