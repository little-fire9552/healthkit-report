"""Analysis tests on the shipped fixture."""

from __future__ import annotations

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from healthkit_report.analysis import analyze, describe, pearson  # noqa: E402
from healthkit_report.parser import parse_export  # noqa: E402

FIXTURE = os.path.join(HERE, "fixtures", "mini_export.xml")


class AnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = parse_export(FIXTURE)
        cls.findings = analyze(cls.dataset)

    def test_span(self):
        span = self.findings["span"]
        self.assertEqual(span["first"], "2024-01-01")
        self.assertEqual(span["last"], "2024-01-02")
        self.assertEqual(span["days"], 2)

    def test_metric_descriptives(self):
        steps = self.findings["metrics"]["steps"]
        self.assertEqual(steps["n"], 2)
        self.assertAlmostEqual(steps["mean"], (1500 + 3000) / 2, delta=1)

    def test_sleep_findings(self):
        sleep = self.findings["sleep"]
        self.assertEqual(sleep["n"], 1)
        self.assertAlmostEqual(sleep["mean"], 6.5, delta=0.05)
        self.assertAlmostEqual(sleep["deep_share"], 1.0 / 6.5, delta=0.01)

    def test_workout_summary(self):
        workouts = self.findings["workouts"]
        self.assertEqual(workouts["count"], 1)  # the 3-minute entry is filtered out
        self.assertEqual(workouts["runs"], 1)
        self.assertAlmostEqual(workouts["run_km"], 5.0, delta=0.1)

    def test_rings(self):
        rings = self.findings["rings"]
        self.assertEqual(rings["days"], 2)
        self.assertAlmostEqual(rings["exercise"], 1.0)  # both days hit the goal

    def test_audio_exposure(self):
        audio = self.findings["audio"]["hp_audio"]
        self.assertAlmostEqual(audio["hours_ge_80"], 1.0, delta=0.01)
        self.assertAlmostEqual(audio["hours_ge_90"], 0.0, delta=0.01)

    def test_describe_and_pearson(self):
        stats = describe([1, 2, 3, 4])
        self.assertAlmostEqual(stats["mean"], 2.5)
        self.assertAlmostEqual(stats["median"], 2.5)
        self.assertAlmostEqual(pearson([(1, 2), (2, 4), (3, 6)] * 4), 1.0, delta=0.001)

    def test_analysis_is_json_serialisable(self):
        import json
        json.dumps(self.findings)


if __name__ == "__main__":
    unittest.main()
