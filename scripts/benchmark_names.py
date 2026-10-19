"""Extraction-only snapshots for flag-off/flag-on comparisons; never renders PNGs.

Example: venv_pathwayextractor/bin/python scripts/benchmark_names.py \
    --zip ~/Downloads/OneDrive_2_2-19-2026.zip --output debug_output/name_benchmark/latest
"""
import argparse
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import time
from zipfile import ZipFile
from contextlib import redirect_stdout, redirect_stderr

from pathway_extractor import extractor
from pathway_extractor.config_generator import analyze_pdf_for_tables
from pathway_extractor.parsers.utils import invert_student_data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--filter")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--files-from", type=Path, help="JSON array of exact PDF filenames")
    parser.add_argument("--repair-wrapped-names", action="store_true")
    args = parser.parse_args()
    mode = "enabled" if args.repair_wrapped_names else "baseline"
    dest = args.output / mode
    dest.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    with args.zip.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    (dest / "manifest.json").write_text(json.dumps({
        "zip": str(args.zip.resolve()), "zip_sha256": digest.hexdigest(),
        "repair_wrapped_names": args.repair_wrapped_names,
    }, indent=2))
    config = json.loads((Path(__file__).resolve().parents[1] /
                         "pathway_extractor/configs/generator_config.json").read_text())
    with ZipFile(args.zip) as archive:
        names = [n for n in archive.namelist() if n.lower().endswith(".pdf")]
        # Match main.py: derive page mapping from the first PDF in the ZIP.
        with redirect_stdout(io.StringIO()):
            found = analyze_pdf_for_tables(io.BytesIO(archive.read(names[0])), config, names[0])
        mapping = {entry["label"]: entry["page_index"] for entry in found}
        for entry in config["table_titles"]:
            entry["page_index"] = mapping[entry["label"]]
    names = [n for n in names if args.filter is None or args.filter in n]
    if args.files_from:
        selected = set(json.loads(args.files_from.read_text()))
        assert selected <= set(names), "Some requested PDFs were not found"
        names = [n for n in names if n in selected]
    if args.limit is not None:
        names = names[:args.limit]
    assert names, "No PDFs selected"
    original = extractor.extract_table_v2
    snapshots = []

    def capture(page, *a, **kw):
        rows, headers = original(page, *a, **kw)
        snapshots.append({"page": page.page_number, "title": a[0],
                          "rows": deepcopy(rows), "headers": headers,
                          "text": page.extract_text(), "words": page.extract_words()})
        return rows, headers

    extractor.extract_table_v2 = capture
    summary = []
    for index, name in enumerate(names, 1):
        snapshots.clear()
        log = io.StringIO()
        start = time.perf_counter()
        kwargs = {"repair_wrapped_names": True} if args.repair_wrapped_names else {}
        with redirect_stdout(log), redirect_stderr(log):
            records = extractor.extract_records_from_zip(
                str(args.zip), filename_filter=name, generator_config=config,
                debug=False, **kwargs)
        assert len(records) == 1, (name, len(records))
        record = records[0]
        aggregated = invert_student_data(deepcopy(record))
        elapsed = time.perf_counter() - start
        result = {"file": name, "seconds": elapsed, "config": config,
                  "raw": deepcopy(snapshots), "record": record,
                  "aggregated": aggregated, "log": log.getvalue()}
        key = hashlib.sha256(name.encode()).hexdigest()[:16]
        (dest / f"{key}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
        summary.append({"file": name, "seconds": elapsed,
                        "students": len(aggregated["students"]), "error": record.get("error")})
        print(f"{index}/{len(names)} {mode}: {name} ({elapsed:.2f}s)", flush=True)
    (dest / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"Saved {len(summary)} PDFs; {sum(r['seconds'] for r in summary):.2f}s; "
          f"{sum(r['error'] is not None for r in summary)} errors", flush=True)


if __name__ == "__main__":
    main()
