"""Verify the benchmark gate detects regressions, not just name-count changes."""
from copy import deepcopy
import unittest

from pathway_extractor.parsers.utils import invert_student_data
from scripts.compare_name_benchmarks import compare


class BenchmarkComparisonTests(unittest.TestCase):
    def samples(self, middle=False):
        rows = [{"student_name": "Long Student", "grammar": 4},
                {"student_name": "Family", "grammar": 0}]
        if middle:
            rows.append({"student_name": "Dawson", "grammar": 0})
        full = "Long Student Family" + (" Dawson" if middle else "")
        record = {"file": "example.pdf", "weekly_submissions": [],
                  "submissions_by_skill": [], "skill_scores": rows}
        before = {"file": "example.pdf", "seconds": 1,
                  "raw": [{"text": "Other Student 1 1 " + full}, {"text": ""}, {"text": ""}],
                  "record": record, "aggregated": invert_student_data(deepcopy(record))}
        after = deepcopy(before)
        after["record"]["skill_scores"] = [{"student_name": full, "grammar": 4}]
        after["aggregated"] = invert_student_data(deepcopy(after["record"]))
        return before, after

    def test_accepts_only_supported_changes(self):
        for middle in (False, True):
            before, after = self.samples(middle)
            self.assertEqual(compare(before, after)["failures"], [])

    def test_rejects_changed_scores(self):
        before, after = self.samples()
        after["record"]["skill_scores"][0]["grammar"] = 3
        self.assertTrue(compare(before, after)["failures"])

    def test_rejects_changed_extraction(self):
        before, after = self.samples()
        after["raw"][0]["text"] += " changed"
        self.assertIn("Raw extraction changed", compare(before, after)["failures"])

    def test_rejects_unexplained_zero_record_removal(self):
        before, after = self.samples()
        before["record"]["skill_scores"].append({"student_name": "Other Person", "grammar": 0})
        self.assertTrue(compare(before, after)["failures"])

    def test_rejects_missing_independent_evidence(self):
        before, after = self.samples()
        before["raw"][0]["text"] = after["raw"][0]["text"] = "Unrelated Person"
        self.assertTrue(compare(before, after)["failures"])

    def test_rejects_unrelated_aggregation_changes(self):
        before, after = self.samples()
        after["aggregated"]["students"]["Other Person"] = {"skill_scores": {"grammar": 0}}
        self.assertIn("Unrelated aggregated student changed", compare(before, after)["failures"])


if __name__ == "__main__":
    unittest.main()
