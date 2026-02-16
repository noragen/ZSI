#!/usr/bin/env python
import unittest

def load_tests_from_test_case(test_case, method_prefix="test"):
    loader = unittest.TestLoader()
    loader.testMethodPrefix = method_prefix
    return loader.loadTestsFromTestCase(test_case)
from ZSI import *
#from ZSI.wstools.logging import setBasicLoggerDEBUG
#setBasicLoggerDEBUG()

class t3TestCase(unittest.TestCase):
    "Test case wrapper for old ZSI t3 test case"

    def checkt3(self):
        a = None
        try:
            3 / 0
        except Exception as e:
            a = e
        f = FaultFromException(a, 0)
        text = f.AsSOAP()
        i = 0
        for l in text.split('\n'):
            #print i, l
            i += 1
        ps = ParsedSoap(text)
        if ps.IsAFault():
            f = FaultFromFaultMessage(ps)
            #print f.AsSOAP()
            self.assertTrue(f.AsSOAP().find(str(a)) > 0)
        #print '--'*20

def makeTestSuite():
    suite = unittest.TestSuite()
    suite.addTest(load_tests_from_test_case(t3TestCase, "check"))
    return suite

def main():
    unittest.main(defaultTest="makeTestSuite")

if __name__ == "__main__" : main()


