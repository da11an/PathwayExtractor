import copy
from contextlib import redirect_stdout, redirect_stderr
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from pathway_extractor.extractor import extract_records_from_zip
from pathway_extractor.parsers.name_repair import repair_supported_names
from pathway_extractor.parsers.page_4 import parse_page_4_table
from pathway_extractor.parsers.utils import invert_student_data


class NameRepairTests(unittest.TestCase):
    def setUp(self):
        self.prefix = "Tagiilimalevalasiesooaiai Pusi"
        self.full = self.prefix + " Salanoa"
        self.rows = [[self.prefix, "4", "4", "4", "-1", "4", "2"],
                     ["Salanoa", "", "", "", "", "", ""]]

    def repair(self, rows=None, known=(), evidence=None):
        return repair_supported_names(self.rows if rows is None else rows, known,
                                      [self.full] if evidence is None else evidence)

    def test_real_failure_and_aggregated_scores(self):
        headers = ["Name", "grammar", "listen", "read", "speak", "vocab", "write"]
        known = {"Phyllis Tavete Salanoa"}
        baseline = parse_page_4_table(self.rows, headers, known_names=known)
        enabled = parse_page_4_table(self.repair(known=known), headers, known_names=known)
        self.assertEqual(len(baseline["skill_scores"]), 2)
        students = invert_student_data(enabled)["students"]
        self.assertEqual(list(students), [self.full])
        self.assertEqual(students[self.full]["skill_scores"],
                         {"grammar": 4, "listening": 4, "reading": 4,
                          "speaking": -1, "vocabulary": 4, "writing": 2})

    def test_requires_exact_independent_evidence(self):
        for evidence in [[], [self.prefix], [self.full + " Other"], ["Other " + self.full]]:
            self.assertEqual(self.repair(evidence=evidence), self.rows)

    def test_does_not_merge_known_predecessor(self):
        self.assertEqual(self.repair(known={self.prefix}), self.rows)

    def test_does_not_merge_known_continuation(self):
        self.assertEqual(self.repair(known={"Salanoa"}), self.rows)

    def test_protects_names_in_independent_roster(self):
        self.assertEqual(self.repair(evidence=[self.full, "Salanoa"]), self.rows)

    def test_explicit_zero_and_placeholder_are_not_continuations(self):
        for value in ["0", 0, "-1", "-", "N/A", "2"]:
            rows = copy.deepcopy(self.rows)
            rows[1][1] = value
            self.assertEqual(self.repair(rows), rows)

    def test_zero_scores_on_first_line_are_preserved(self):
        rows = [[self.prefix] + ["0"] * 6, self.rows[1]]
        self.assertEqual(self.repair(rows), [[self.full] + ["0"] * 6])

    def test_blank_extraction_gaps(self):
        rows = [self.rows[0], [None] * 7, [" "] * 7, self.rows[1]]
        self.assertEqual(self.repair(rows), [[self.full] + self.rows[0][1:]])

    def test_three_line_name_and_ambiguous_evidence(self):
        rows = [["Long First", "1"], ["Middle", ""], ["Last", ""]]
        self.assertEqual(self.repair(rows, evidence=["Long First Middle Last"]),
                         [["Long First Middle Last", "1"]])
        self.assertEqual(self.repair(rows, evidence=["Long First Middle", "Long First Middle Last"]), rows)

    def test_does_not_borrow_values_from_next_student(self):
        rows = [[self.prefix] + [""] * 6, ["Salanoa", "1", "", "", "", "", ""]]
        self.assertEqual(self.repair(rows), rows)

    def test_unicode_case_and_spacing(self):
        rows = [["María de", "2"], ["Ávila", ""]]
        self.assertEqual(self.repair(rows, evidence=[" MARÍA  DE ÁVILA "]), [["María de Ávila", "2"]])

    def test_does_not_mutate_inputs(self):
        original = copy.deepcopy(self.rows)
        result = self.repair()
        self.assertEqual(self.rows, original)
        result[0][1] = "999"
        self.assertEqual(self.rows, original)

    def test_side_by_side_roster_separated_by_numeric_cells(self):
        self.assertEqual(self.repair(evidence=["Other Student 17 17 " + self.full]),
                         [[self.full] + self.rows[0][1:]])

    def test_never_joins_across_numeric_cells_or_lines(self):
        for evidence in [[self.prefix + " 1 Salanoa"], [self.prefix, "Salanoa"],
                         ["Other Student " + self.full]]:
            self.assertEqual(self.repair(evidence=evidence), self.rows)


class ExtractionFlagTests(unittest.TestCase):
    """Exercise the real parser orchestration with a controlled PDF boundary."""

    def extract(self, enabled, independent=True, already_known=False):
        full = "Long Student Family Dawson"
        weekly = [[full if already_known else "Other Student", "1", "1"]]
        skill = [[weekly[0][0], "1", "1"]]
        levels = [["Long Student Family", "4", "4", "4", "-1", "4", "2"],
                  ["Dawson", "", "", "", "", "", ""]]
        tables = [(weekly, ["Name", "1", "Total"]),
                  (skill, ["Name", "read", "Total"]),
                  (levels, ["Name", "grammar", "listen", "read", "speak", "vocab", "write"])]

        class Page:
            def __init__(self, index):
                self.index = index
                self.calls = 0

            def extract_text(self):
                self.calls += 1
                if self.index == 0 and independent:
                    return "Other Student 1 1 " + full
                return full if self.index == 2 else ""

        class PDF:
            pages = [Page(i) for i in range(3)]

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        pdf = PDF()
        config = {"table_titles": [
            {"label": f"page{i + 2}_text", "page_index": i, "title_text": str(i),
             "parser_module": f"pathway_extractor.parsers.page_{i + 2}",
             "parser_function": f"parse_page_{i + 2}_table"}
            for i in range(3)]}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "class.zip"
            with ZipFile(path, "w") as archive:
                archive.writestr("Utah EC3, V, Thursday, 10-00 AM - Example.pdf", b"fake")
            with patch("pathway_extractor.extractor.pdfplumber.open", return_value=pdf), \
                 patch("pathway_extractor.extractor.extract_table_v2",
                       side_effect=lambda page, *a, **kw: copy.deepcopy(tables[page.index])), \
                 redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                record = extract_records_from_zip(str(path), generator_config=config,
                                                  repair_wrapped_names=enabled, debug=False)[0]
        self.assertNotIn("error", record)
        return record, sum(page.calls for page in pdf.pages)

    def test_flag_defaults_to_original_behavior(self):
        baseline, text_calls = self.extract(False)
        fixed, _ = self.extract(True)
        self.assertEqual(text_calls, 0)
        self.assertEqual(len(baseline["skill_scores"]), 2)
        self.assertEqual(len(fixed["skill_scores"]), 1)
        self.assertEqual(fixed["skill_scores"][0]["student_name"], "Long Student Family Dawson")
        for section in ("weekly_submissions", "submissions_by_skill"):
            self.assertEqual(baseline[section], fixed[section])

    def test_evidence_on_same_page_is_not_independent(self):
        baseline, _ = self.extract(False, independent=False)
        fixed, _ = self.extract(True, independent=False)
        self.assertEqual(baseline, fixed)

    def test_already_handled_wrap_unchanged(self):
        baseline, _ = self.extract(False, already_known=True)
        fixed, _ = self.extract(True, already_known=True)
        self.assertEqual(baseline, fixed)

    def test_legacy_extraction_rejects_unsupported_flag(self):
        with self.assertRaisesRegex(ValueError, "v2"):
            extract_records_from_zip("unused.zip", repair_wrapped_names=True)


if __name__ == "__main__":
    unittest.main()
