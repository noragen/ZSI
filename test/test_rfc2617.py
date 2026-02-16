#!/usr/bin/env python
"""
RFC2617

HTTP Authentication: Basic and Digest Access Authentication
"""

import unittest

def load_tests_from_test_case(test_case, method_prefix="test"):
    loader = unittest.TestLoader()
    loader.testMethodPrefix = method_prefix
    return loader.loadTestsFromTestCase(test_case)

from ZSI import digest_auth

class DATestCase(unittest.TestCase):
    "test Union TypeCode"

    def check_challenge_single_www_authenticate_header(self):
        challenge='Basic realm="WallyWorld"'
        #print "=="*30
        #print challenge
        #print "=="*30
        cd = digest_auth.fetch_challenge(challenge)
        expect = {'challenge': 'Basic', 'realm': 'WallyWorld'}
        self.assertTrue(cd == expect, 'Expected equivalent')

    def check_challenge_single_www_authenticate_header2(self):
        challenge='Basic realm="Wally World"'
        cd = digest_auth.fetch_challenge(challenge)
        expect = {'challenge': 'Basic', 'realm': 'Wally World'}
        self.assertTrue(cd == expect, 'Expected equivalent')

    def check_challenge_single_www_authenticate_header3(self):
        challenge = '''Digest
                 realm="testrealm@host.com",
                 qop="auth,auth-int",
                 nonce="dcd98b7102dd2f0e8b11d0f600bfb0c093",
                 opaque="5ccc069c403ebaf9f0171e9517f40e41"'''
        cd = digest_auth.fetch_challenge(challenge)
        expect = {'nonce': 'dcd98b7102dd2f0e8b11d0f600bfb0c093', 'challenge': 'Digest', 'opaque': '5ccc069c403ebaf9f0171e9517f40e41', 'realm': 'testrealm@host.com', 'qop': 'auth,auth-int'}
        self.assertTrue(cd == expect, 'Expected equivalent')

def makeTestSuite():
    suite = unittest.TestSuite()
    suite.addTest(load_tests_from_test_case(DATestCase, "check"))
    return suite

def main():
    unittest.main(defaultTest="makeTestSuite")

if __name__ == '__main__':
    main()


