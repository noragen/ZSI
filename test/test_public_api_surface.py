import unittest

import ZSI


EXPECTED_PUBLIC_API = {
    "Fault",
    "FaultException",
    "FaultFromActor",
    "FaultFromException",
    "FaultFromFaultMessage",
    "FaultFromNotUnderstood",
    "FaultFromZSIException",
    "ParseException",
    "ParsedSoap",
    "SoapWriter",
    "TC",
    "UNICODE_ENCODING",
    "Version",
    "ZSIException",
}


class PublicAPISurfaceTests(unittest.TestCase):
    def test_expected_public_symbols_exist(self):
        actual = set(dir(ZSI))
        missing = sorted(EXPECTED_PUBLIC_API - actual)
        self.assertEqual(missing, [], f"missing public API symbols: {missing}")


def makeTestSuite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(PublicAPISurfaceTests)


if __name__ == "__main__":
    unittest.main(defaultTest="makeTestSuite")
