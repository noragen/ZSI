import unittest

from ZSI.fault import FaultFromException


class FaultDiagnosticsTests(unittest.TestCase):
    def test_fault_contains_request_id_and_context(self):
        try:
            raise RuntimeError("boom")
        except RuntimeError as exc:
            fault = FaultFromException(
                exc,
                0,
                request_id="req-1234",
                context_summary="RuntimeError: boom ; at module.py:1:test",
            )

        text = str(fault)
        self.assertIn("req-1234", text)
        self.assertIn("context", text)
        soap = fault.AsSOAP()
        self.assertIn("request_id=req-1234", soap)


def makeTestSuite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(FaultDiagnosticsTests)


if __name__ == "__main__":
    unittest.main(defaultTest="makeTestSuite")
