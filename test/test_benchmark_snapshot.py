#!/usr/bin/env python
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from scripts.benchmark_snapshot import compare_to_history


class BenchmarkSnapshotTests(unittest.TestCase):
    def test_warns_on_mean_regression(self):
        current = {
            "results": [
                {"name": "test_zsi", "mean_seconds": 12.0},
            ]
        }
        history = [
            {"payload": {"results": [{"name": "test_zsi", "mean_seconds": 10.0}]}},
            {"payload": {"results": [{"name": "test_zsi", "mean_seconds": 10.0}]}},
            {"payload": {"results": [{"name": "test_zsi", "mean_seconds": 10.0}]}},
        ]
        warnings, info = compare_to_history(
            current=current,
            history=history,
            warn_regression=0.10,
            min_history=3,
        )
        self.assertEqual([], info)
        self.assertEqual(1, len(warnings))
        self.assertIn("test_zsi", warnings[0])


def makeTestSuite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(BenchmarkSnapshotTests)


if __name__ == "__main__":
    unittest.main(defaultTest="makeTestSuite")
