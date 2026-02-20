#!/usr/bin/env python
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from scripts.build_dashboards import build_dashboard_markdown


class BuildDashboardsTests(unittest.TestCase):
    def test_generates_markdown_with_perf_table(self):
        md = build_dashboard_markdown(
            benchmark_smoke={
                "results": [
                    {
                        "name": "test_zsi",
                        "mean_seconds": 1.1,
                        "max_seconds": 1.4,
                        "budget_seconds": 2.0,
                        "ok": True,
                    }
                ]
            },
            benchmark_history={"history": [{"payload": {}}, {"payload": {}}]},
        )
        self.assertIn("ZSI CI Artifact Dashboard", md)
        self.assertIn("| test_zsi | 1.100 | 1.400 | 2.000 | PASS |", md)
        self.assertIn("History snapshots: `2`", md)


def makeTestSuite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(BuildDashboardsTests)


if __name__ == "__main__":
    unittest.main(defaultTest="makeTestSuite")
