#!/usr/bin/env python
import unittest

from ZSI.telemetry import span


class TelemetryHooksTests(unittest.TestCase):
    def test_span_context_manager_works_without_otel(self):
        with span("test.telemetry.hook", sample_attr="value") as handle:
            # Either a real OTel span or None (no-op mode) is acceptable.
            self.assertTrue(handle is None or hasattr(handle, "set_attribute"))


def makeTestSuite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(TelemetryHooksTests)


if __name__ == "__main__":
    unittest.main(defaultTest="makeTestSuite")
