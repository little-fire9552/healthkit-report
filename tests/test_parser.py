"""Parser tests: de-duplication, unit normalisation, sleep and workouts."""

from __future__ import annotations

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from healthkit_report.parser import parse_export  # noqa: E402

FIXTURE = os.path.join(HERE, "fixtures", "mini_export.xml")


class ParseFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = parse_export(FIXTURE)
        cls.daily = cls.dataset["daily"]

    def test_meta(self):
        meta = self.dataset["meta"]
        self.assertEqual(meta["export_date"], "2024-01-04 10:00:00 +0800")
        self.assertEqual(meta["me"]["HKCharacteristicTypeIdentifierDateOfBirth"], "2000-05-01")
        self.assertGreater(meta["record_count"], 15)

    def test_steps_are_deduplicated(self):
        # Watch: 600 + 400 = 1000 over 10:00-10:20.
        # iPhone duplicates that window and adds 500 at 11:00.
        self.assertAlmostEqual(self.daily["2024-01-01"]["steps"], 1500, delta=1.0)

    def test_energy_is_not_double_counted(self):
        # Watch 420 and iPhone 410 cover the same day: keep the watch value.
        self.assertAlmostEqual(self.daily["2024-01-01"]["active_energy"], 420, delta=30)

    def test_heart_rate_mean_ignores_duplicate_sample(self):
        values = [self.daily["2024-01-01"]["hr"]]
        self.assertAlmostEqual(values[0], 80.0, delta=1.0)  # (60 + 80 + 100) / 3

    def test_percentage_normalisation(self):
        self.assertAlmostEqual(self.daily["2024-01-01"]["spo2"], 97.0, delta=0.5)
        self.assertAlmostEqual(self.daily["2024-01-02"]["dbl_support"], 28.0, delta=1.0)

    def test_distance_and_speed(self):
        self.assertAlmostEqual(self.daily["2024-01-02"]["walk_dist"], 2.4, delta=0.05)
        self.assertAlmostEqual(self.daily["2024-01-02"]["walk_speed"], 4.8, delta=0.05)

    def test_sleep_is_attributed_to_wake_date(self):
        sleep = self.dataset["sleep"]["2024-01-02"]
        self.assertAlmostEqual(sleep["asleep"], 6.5, delta=0.05)
        self.assertAlmostEqual(sleep["deep"], 1.0, delta=0.05)
        self.assertAlmostEqual(sleep["rem"], 1.5, delta=0.05)
        self.assertEqual(self.daily["2024-01-02"]["sleep_start"], "23:30")

    def test_workouts(self):
        workouts = self.dataset["workouts"]
        self.assertEqual(len(workouts), 2)
        run = workouts[0]
        self.assertEqual(run["type"], "Running")
        self.assertAlmostEqual(run["duration_min"], 30.0)
        self.assertAlmostEqual(run["statistics"]["DistanceWalkingRunning"]["sum"], 5.0)
        self.assertAlmostEqual(run["energy"], 300.0)

    def test_activity_summary(self):
        self.assertEqual(len(self.dataset["activity"]), 2)
        self.assertEqual(self.dataset["activity"][0]["date"], "2024-01-01")

    def test_audio_histogram(self):
        histogram = self.dataset["audio"]["hp_audio"]
        self.assertAlmostEqual(histogram["85"], 3600, delta=1)
        self.assertAlmostEqual(histogram["70"], 3600, delta=1)

    def test_date_filter(self):
        filtered = parse_export(FIXTURE, since="2024-01-02", until="2024-01-02")
        self.assertEqual(sorted(filtered["daily"]), ["2024-01-02"])

    def test_priority_order_can_be_inverted(self):
        dataset = parse_export(FIXTURE, device_priority=["iPhone", "Watch"])
        # iPhone covers 10:00-10:20 and 11:00, i.e. 590 + 395 + 500
        self.assertAlmostEqual(dataset["daily"]["2024-01-01"]["steps"], 1485, delta=5)


if __name__ == "__main__":
    unittest.main()
