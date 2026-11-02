"""Reference grading + renderer smoke tests."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from healthkit_report.analysis import analyze  # noqa: E402
from healthkit_report.parser import parse_export  # noqa: E402
from healthkit_report.references import (  # noqa: E402
    NORMAL,
    Reference,
    default_references,
    profile_from_dataset,
)

FIXTURE = os.path.join(HERE, "fixtures", "mini_export.xml")


class ReferenceTests(unittest.TestCase):
    def test_grades(self):
        ref = Reference("x", "测试", "test", "生命体征", low=60, high=100)
        self.assertEqual(ref.grade(80), NORMAL)
        self.assertEqual(ref.grade(50), "偏低")
        self.assertEqual(ref.grade(120), "偏高")
        self.assertEqual(ref.grade(None), "未检测")

    def test_caution_band(self):
        ref = Reference("x", "测试", "test", "生命体征", low=60, high=100, caution_high=65)
        self.assertEqual(ref.grade(70), "正常偏高")

    def test_default_table_is_unique_and_complete(self):
        refs = default_references()
        keys = [ref.key for ref in refs]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertIn("vo2max", keys)
        self.assertIn("sleep_h", keys)

    def test_profile_from_dataset(self):
        dataset = parse_export(FIXTURE)
        profile = profile_from_dataset(dataset)
        self.assertEqual(profile["sex"], "男")
        self.assertEqual(profile["birth_date"], "2000-05-01")
        self.assertIsNotNone(profile["age"])


class RendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = parse_export(FIXTURE)
        cls.findings = analyze(cls.dataset)
        cls.tmp = tempfile.TemporaryDirectory(prefix="hkrep-test-")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_docx(self):
        from docx import Document

        from healthkit_report.render.docx import build_report

        path = os.path.join(self.tmp.name, "report.docx")
        build_report(self.dataset, self.findings, path, name="测试用户")
        self.assertGreater(os.path.getsize(path), 10_000)
        doc = Document(path)
        text = "\n".join(paragraph.text for paragraph in doc.paragraphs)
        self.assertIn("健康体检报告", text)
        self.assertTrue(any("检查项目" in cell.text for table in doc.tables for row in table.rows
                            for cell in row.cells))

    def test_html(self):
        from healthkit_report.render.html import build_dashboard

        html = build_dashboard(self.dataset, self.findings, name="测试用户")
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("<svg", html)
        self.assertIn("测试用户", html)

    def test_xlsx(self):
        from healthkit_report.render.xlsx import build_workbook

        path = os.path.join(self.tmp.name, "report.xlsx")
        build_workbook(self.dataset, self.findings, path)
        self.assertGreater(os.path.getsize(path), 5_000)
        try:
            from openpyxl import load_workbook
        except ImportError:  # optional dependency, skip the structural check
            return
        workbook = load_workbook(path)
        self.assertEqual(workbook.sheetnames[:3], ["概览", "每日指标", "月度汇总"])
        self.assertGreater(workbook["每日指标"].max_row, 2)


if __name__ == "__main__":
    unittest.main()


class MeasurementConsistencyTests(unittest.TestCase):
    """封面和表格必须使用同一次测量（最近一条），否则报告自相矛盾。"""

    def test_table_height_matches_profile(self):
        from healthkit_report.render.docx import _row_values

        findings = {"metrics": {"height": {"mean": 170.0, "unit": "cm", "digits": 0}}}
        profile = {"height_cm": 168.0, "weight_kg": 69.4}
        values = _row_values(findings, profile)
        self.assertEqual(values["height"][0], 168.0)
        self.assertEqual(values["weight"][0], 69.4)

    def test_vo2max_threshold_depends_on_sex_and_age(self):
        from healthkit_report.references import default_references

        male_21 = {r.key: r for r in default_references(sex="男", age=21)}["vo2max"]
        female_21 = {r.key: r for r in default_references(sex="女", age=21)}["vo2max"]
        self.assertEqual(male_21.grade(33.7), "偏低")
        self.assertEqual(female_21.grade(33.7), "正常")


class SleepAndGradingTests(unittest.TestCase):
    def test_short_sleep_counts_as_nap(self):
        from healthkit_report.analysis import analyze

        dataset = {
            "meta": {},
            "daily": {"2024-01-02": {"sleep_h": 7.0, "steps": 8000},
                      "2024-01-03": {"nap_h": 1.5, "steps": 7000}},
            "sleep": {"2024-01-02": {"asleep": 7.0, "deep": 1.0, "rem": 1.5, "core": 4.5,
                                     "awake": 0.2, "inbed": 7.5, "start": "2024-01-02 23:00:00 +0800",
                                     "end": "2024-01-03 06:30:00 +0800"},
                      "2024-01-03": {"asleep": 1.5, "deep": 0.2, "rem": 0.3, "core": 1.0,
                                     "awake": 0.0, "inbed": 1.5, "start": "2024-01-03 13:00:00 +0800",
                                     "end": "2024-01-03 14:30:00 +0800"}},
            "workouts": [], "activity": [], "audio": {},
        }
        findings = analyze(dataset)
        self.assertEqual(findings["sleep"]["n"], 1)
        self.assertAlmostEqual(findings["sleep"]["mean"], 7.0, delta=0.01)
        self.assertEqual(findings["sleep"]["naps"], 1)
        self.assertAlmostEqual(findings["sleep"]["nap_hours"], 1.5, delta=0.01)

    def test_vo2max_bands(self):
        from healthkit_report.references import default_references

        ref = {r.key: r for r in default_references(sex="男", age=21)}["vo2max"]
        self.assertEqual(ref.grade(38.3), "正常偏低")  # 37.4–40.1
        self.assertEqual(ref.grade(36.0), "偏低")      # < 37.4
        self.assertEqual(ref.grade(45.0), "正常")
