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
