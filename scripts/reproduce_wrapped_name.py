"""Reproduce a wrapped student name becoming two records in a single real PDF.

Run from the repository root with:
    venv_pathwayextractor/bin/python scripts/reproduce_wrapped_name.py

Uses the locally downloaded ZIP; does not change production reports or configs.
An assertion failure means the observed bug no longer matches this reproduction.
"""

import argparse
from copy import deepcopy
import io
import json
from pathlib import Path
from zipfile import ZipFile

import pdfplumber

from pathway_extractor.extractor import extract_records_from_zip, extract_table_v2
from pathway_extractor.parsers.utils import invert_student_data, merge_wrapped_name_rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, default=Path.home() / "Downloads/OneDrive_2_2-19-2026.zip")
    parser.add_argument("--repair-wrapped-names", action="store_true",
                        help="Verify the opt-in fix instead of reproducing the original split")
    args = parser.parse_args()
    config_path = Path(__file__).resolve().parents[1] / "pathway_extractor/configs/generator_config.json"
    config = json.loads(config_path.read_text())
    with ZipFile(args.zip) as archive:
        matches = [name for name in archive.namelist() if "Jahnke" in name and name.endswith(".pdf")]
        assert len(matches) == 1, f"Expected one Jahnke PDF, found {matches}"
        filename = matches[0]
        with pdfplumber.open(io.BytesIO(archive.read(filename))) as pdf:
            for entry in config["table_titles"]:
                indices = [i for i, page in enumerate(pdf.pages)
                           if entry["title_text"] in (page.extract_text() or "")]
                assert len(indices) == 1, (entry["label"], indices)
                entry["page_index"] = indices[0]
            entry = next(t for t in config["table_titles"] if t["label"] == "page4_text")
            rows, _ = extract_table_v2(
                pdf.pages[entry["page_index"]], entry["title_text"],
                entry["expected_first_column_header"], entry["expected_last_column_header"],
            )

    records = extract_records_from_zip(str(args.zip), filename_filter=filename,
                                       generator_config=config, debug=False,
                                       repair_wrapped_names=args.repair_wrapped_names)
    assert len(records) == 1 and "error" not in records[0], records
    record = records[0]
    prefix = "Tagiilimalevalasiesooaiai Pusi"
    suffix = "Salanoa"
    full_name = f"{prefix} {suffix}"
    index = next(i for i, row in enumerate(rows) if row[0] == prefix)
    fragments = rows[index:index + 2]
    assert fragments[1][0] == suffix and not any(fragments[1][1:]), fragments
    known_names = {row["student_name"] for row in record["weekly_submissions"]}
    assert full_name not in known_names
    # The cross-page validation prevents an otherwise successful wrapped-row merge.
    assert merge_wrapped_name_rows(fragments)[0][0] == full_name
    assert len(merge_wrapped_name_rows(fragments, known_names=known_names)) == 2
    students = invert_student_data(deepcopy(record))["students"]
    if args.repair_wrapped_names:
        assert full_name in students and prefix not in students and suffix not in students
        assert students[full_name]["skill_scores"] == {
            "grammar": 4, "listening": 4, "reading": 4,
            "speaking": -1, "vocabulary": 4, "writing": 2,
        }
        print(f"FIX VERIFIED: one student named {full_name!r}, original scores preserved.")
        return
    assert full_name not in students
    assert prefix in students and suffix in students
    assert all(value == 0 for value in students[suffix]["skill_scores"].values())
    print(f"Source: {args.zip}\nClass: {filename}")
    print("Raw wrapped rows:", json.dumps(fragments, ensure_ascii=False))
    print("Actual separate student records:")
    print(json.dumps({name: students[name] for name in (prefix, suffix)}, indent=2))
    print(f"REPRODUCED: expected one student named {full_name!r}; got two fragments.")


if __name__ == "__main__":
    main()
