import io
import json
import unittest

from ZSI.wstools.logging import JSONLogger


class StructuredLoggingTests(unittest.TestCase):
    def test_json_logger_emits_expected_schema(self):
        sink = io.StringIO()
        logger = JSONLogger("ZSI.test", out=sink)
        logger.setLevel(2)
        logger.debug("hello %s", "world", event="resolver.fetch", uri="https://example.org/x")

        line = sink.getvalue().strip()
        payload = json.loads(line)
        self.assertEqual(payload["component"], "ZSI.test")
        self.assertEqual(payload["event"], "resolver.fetch")
        self.assertEqual(payload["level"], "DEBUG")
        self.assertEqual(payload["message"], "hello world")
        self.assertEqual(payload["uri"], "https://example.org/x")
        self.assertIn("ts", payload)


def makeTestSuite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(StructuredLoggingTests)


if __name__ == "__main__":
    unittest.main(defaultTest="makeTestSuite")
