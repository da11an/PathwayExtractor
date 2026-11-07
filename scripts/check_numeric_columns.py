"""Replay saved PDF words through both column rules and the production parsers.

Usage: python scripts/check_numeric_columns.py SNAPSHOT_DIRECTORY --report PATH
SNAPSHOT_DIRECTORY is the enabled/ directory produced by benchmark_names.py.
No PNGs or production reports are created. The source ZIP must still be present.
"""
import argparse
from collections import Counter
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import io
import json
from pathlib import Path
import re
from types import SimpleNamespace
from unittest.mock import patch

from pathway_extractor import extractor
from pathway_extractor.parsers.utils import invert_student_data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshots", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((args.snapshots / "manifest.json").read_text())
    word_extractor = extractor.extract_table_by_words
    table_extractor = extractor.extract_table_v2
    results = []

    def legacy_words(*a, **kw):
        kw.pop("header_positions", None)
        return word_extractor(*a, **kw)

    for path in sorted(args.snapshots.glob("*.json")):
        if path.name in ("summary.json", "manifest.json"):
            continue
        saved = json.loads(path.read_text())
        raw = saved["raw"]
        pages = [SimpleNamespace(extract_words=lambda: [], extract_text=lambda: "")
                 for _ in range(max(r["page"] for r in raw))]
        for r in raw:
            pages[r["page"] - 1] = SimpleNamespace(
                extract_words=lambda r=r: deepcopy(r["words"]),
                extract_text=lambda r=r: r["text"], page_number=r["page"])

        class PDF:
            def __enter__(self):
                return SimpleNamespace(pages=pages)

            def __exit__(self, *unused):
                pass

        deltas = []

        def checked_table(page, *a, **kw):
            source = next(r for r in raw if r["page"] == page.page_number and r["title"] == a[0])
            with patch.object(extractor, "extract_table_by_words", legacy_words):
                old, old_headers = table_extractor(page, *a, **kw)
            new, headers = table_extractor(page, *a, **kw)
            assert old == source["rows"] and old_headers == source["headers"], "Legacy raw replay differs"
            assert headers == old_headers and len(old) == len(new), "Table layout changed"
            for row_index, (left, right) in enumerate(zip(old, new)):
                if left == right:
                    continue
                # Every token stays on its original row. Only integer tokens may
                # change columns; all names and other text retain their columns.
                tokens = lambda row: Counter(word for cell in row for word in cell.split())
                assert tokens(left) == tokens(right), "Lost or duplicated PDF text"
                text_cells = lambda row: [[w for w in cell.split() if not re.fullmatch(r"-?\d+", w)] for cell in row]
                assert text_cells(left) == text_cells(right), "Moved nonnumeric text"
                if headers[-1].lower() == "total":
                    assert all(not v or re.fullmatch(r"-?\d+", v) for v in right[1:]), "Ambiguous numeric cell"
                    values = [int(v or 0) for v in right[1:]]
                    assert sum(values[:-1]) == values[-1], "Corrected values do not sum to the printed total"
                deltas.append({"page": page.page_number, "row": row_index,
                               "before": left, "after": right})
            return new, headers

        kwargs = dict(zip_path=manifest["zip"], filename_filter=saved["file"],
                      generator_config=saved["config"], debug=False, repair_wrapped_names=True)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()), \
             patch.object(extractor.pdfplumber, "open", return_value=PDF()):
            with patch.object(extractor, "extract_table_by_words", legacy_words):
                old_record = extractor.extract_records_from_zip(**kwargs)[0]
            assert old_record == saved["record"], "Legacy parsed replay differs"
            with patch.object(extractor, "extract_table_v2", checked_table):
                new_record = extractor.extract_records_from_zip(**kwargs)[0]
        assert "error" not in new_record, new_record
        # If the raw input is identical, downstream behavior must be identical too.
        assert deltas or old_record == new_record, "Unexplained parser change"
        results.append({"file": saved["file"], "raw_changes": deltas,
                        "record_changed": old_record != new_record,
                        "record": new_record,
                        "aggregated": invert_student_data(deepcopy(new_record))})

    report = {"pdfs": len(results), "classes_with_changes": sum(bool(r["raw_changes"]) for r in results),
              "changed_rows": sum(len(r["raw_changes"]) for r in results), "results": results}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "results"}))


if __name__ == "__main__":
    main()
