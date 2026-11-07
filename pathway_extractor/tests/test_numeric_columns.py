"""Regression coverage for right-aligned counts crossing header-based boundaries."""
import unittest
from types import SimpleNamespace

from pathway_extractor.extractor import compute_column_boundaries, extract_table_by_words
from pathway_extractor.parsers.page_2 import parse_page_2_table
from pathway_extractor.parsers.utils import invert_student_data


class NumericColumnTests(unittest.TestCase):
    def setUp(self):
        # Header coordinates from the November Shirley report, rounded to 0.001pt.
        self.headers = [("Name", 100.5, 158.825), ("1", 486.773, 499.485),
                        ("2", 533.273, 545.985), ("Total", 564.3, 620.99)]

    def extract(self, words, headers=None, align=True):
        headers = self.headers if headers is None else headers
        page = SimpleNamespace(extract_words=lambda: [
            {"text": text, "x0": left, "x1": right, "top": 300, "bottom": 320}
            for text, left, right in words])
        return extract_table_by_words(page, compute_column_boundaries(headers),
                                      [h[0] for h in headers], 280, 350,
                                      header_positions=headers if align else None)

    def test_three_digit_week_one_count_and_cross_page_aggregation(self):
        words = [("Test Student", 100.5, 330), ("105", 461.344, 499.479),
                 ("2", 533.273, 545.985), ("107", 582.85, 620.99)]
        self.assertEqual(self.extract(words, align=False)[0], ["Test Student 105", "", "2", "107"])
        fixed = self.extract(words)
        self.assertEqual(fixed[0], ["Test Student", "105", "2", "107"])
        record = parse_page_2_table(fixed, [h[0] for h in self.headers], target_header="Name")
        record["skill_scores"] = [{"student_name": "Test Student", "grammar": 3}]
        students = invert_student_data(record)["students"]
        self.assertEqual(list(students), ["Test Student"])
        self.assertEqual(students["Test Student"]["weekly_submissions"],
                         {"week_1": 105, "week_2": 2, "total": 107})
        self.assertEqual(students["Test Student"]["skill_scores"], {"grammar": 3})

    def test_bold_total_counts_stay_in_their_own_columns(self):
        rows = self.extract([("Total", 100.5, 157.156), ("319", 456.844, 499.489),
                             ("70", 517.547, 545.977), ("389", 578.344, 620.989)])
        self.assertEqual(rows, [["Total", "319", "70", "389"]])
        self.assertEqual(parse_page_2_table(rows, [h[0] for h in self.headers]), {"weekly_submissions": []})

    def test_large_later_week_does_not_join_previous_week(self):
        rows = self.extract([("Test Student", 100.5, 330), ("1", 486.773, 499.485),
                             ("105", 507.85, 545.98), ("106", 582.85, 620.99)])
        self.assertEqual(rows, [["Test Student", "1", "105", "106"]])

    def test_name_words_never_use_numeric_alignment(self):
        self.assertEqual(self.extract([("Longlastname", 400, 499.48)])[0], ["Longlastname", "", "", ""])

    def test_unconfirmed_numeric_alignment_keeps_original_placement(self):
        words = [("105", 440, 478)]
        self.assertEqual(self.extract(words), self.extract(words, align=False))

    def test_ambiguous_header_alignment_keeps_original_placement(self):
        headers = [("Name", 100, 150), ("1", 200, 220), ("2", 210, 220.5)]
        words = [("105", 179, 220)]
        self.assertEqual(self.extract(words, headers), self.extract(words, headers, align=False))

    def test_one_and_two_digit_counts_still_work(self):
        for value, left in [("1", 486.773), ("17", 474.06)]:
            self.assertEqual(self.extract([(value, left, 499.48)])[0], ["", value, "", ""])

    def test_negative_values_align_without_losing_sign(self):
        self.assertEqual(self.extract([("-1", 475, 499.48)])[0], ["", "-1", "", ""])


if __name__ == "__main__":
    unittest.main()
