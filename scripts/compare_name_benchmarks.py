"""Fail on unexpected extraction or data changes; save every name-repair delta."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re

from pathway_extractor.parsers.name_repair import normalize_name

SECTIONS = ("weekly_submissions", "submissions_by_skill", "skill_scores")


def metrics(record):
    sets = [{r.get("student_name") for r in record.get(s, [])} for s in SECTIONS]
    return {"rows": {s: len(record.get(s, [])) for s in SECTIONS},
            "distinct_names": len(set.union(*sets)),
            "names_on_all_three": len(set.intersection(*sets)),
            "duplicate_names": sum(len(record.get(s, [])) - len(ns) for s, ns in zip(SECTIONS, sets))}


def compare(before, after):
    failures, changes = [], []
    if before["raw"] != after["raw"]:
        failures.append("Raw extraction changed")
    a, b = before["record"], after["record"]
    if "error" in a or "error" in b:
        failures.append("Extraction error")
    if {k: v for k, v in a.items() if k not in SECTIONS} != {k: v for k, v in b.items() if k not in SECTIONS}:
        failures.append("Metadata changed")
    for section in SECTIONS:
        old, new = a.get(section, []), b.get(section, [])
        if old == new:
            continue
        removed = [r for r in old if r not in new]
        added = [r for r in new if r not in old]
        changes.append({"section": section, "removed": removed, "added": added})
        # Preserve multiplicity and every nonzero numeric payload, including -1.
        def payloads(rows):
            return Counter(json.dumps({k: v for k, v in r.items() if k != "student_name"}, sort_keys=True)
                           for r in rows if any(v != 0 for k, v in r.items() if k != "student_name"))
        if payloads(old) != payloads(new):
            failures.append(f"{section}: numeric payloads changed")
        remaining = list(removed)
        for row in added:
            full = row["student_name"]
            # Each added full name must replace an existing prefix with identical values.
            sources = [r for r in remaining if full.startswith(r["student_name"] + " ")
                       and {k: v for k, v in r.items() if k != "student_name"}
                       == {k: v for k, v in row.items() if k != "student_name"}]
            if len(sources) != 1:
                failures.append(f"{section}: ambiguous or missing source for {full}")
                continue
            source = sources[0]
            remaining.remove(source)
            suffix = full[len(source["student_name"]):].strip()
            fragments = []
            joined = ""
            for fragment in old[old.index(source) + 1:]:
                if fragment not in remaining or any(v != 0 for k, v in fragment.items() if k != "student_name"):
                    break
                fragments.append(fragment)
                joined = " ".join(r["student_name"] for r in fragments)
                if joined == suffix or not suffix.startswith(joined + " "):
                    break
            if joined == suffix:
                for fragment in fragments:
                    remaining.remove(fragment)
            else:
                failures.append(f"{section}: missing unique zero-valued continuation for {full}")
            page = {"weekly_submissions": 0, "submissions_by_skill": 1, "skill_scores": 2}[section]
            evidence = [line for idx, raw in enumerate(before["raw"]) if idx != page
                        for line in (raw["text"] or "").splitlines()]
            runs = [part for line in evidence
                    for part in re.split(r"(?<!\S)[+-]?\d+(?:\.\d+)?(?!\S)", line)]
            if normalize_name(full) not in {normalize_name(line) for line in runs}:
                failures.append(f"{section}: no independent full-name evidence for {full}")
        if remaining:
            failures.append(f"{section}: unexplained removed rows {remaining}")
    if metrics(b)["duplicate_names"] > metrics(a)["duplicate_names"]:
        failures.append("Introduced duplicate student names")
    # Inversion may overwrite same-name rows; explicitly verify unrelated students.
    altered = {r["student_name"] for c in changes for r in c["removed"] + c["added"]}
    sa, sb = before["aggregated"]["students"], after["aggregated"]["students"]
    if {k: v for k, v in sa.items() if k not in altered} != {k: v for k, v in sb.items() if k not in altered}:
        failures.append("Unrelated aggregated student changed")
    return {"file": before["file"], "before": metrics(a), "after": metrics(b),
            "changes": changes, "failures": failures,
            "baseline_seconds": before["seconds"], "enabled_seconds": after["seconds"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--report", default="comparison.json")
    parser.add_argument("--require-complete", action="store_true",
                        help="Require matching complete baseline/enabled PDF sets")
    args = parser.parse_args()
    results = []
    excluded = {"summary.json", "manifest.json"}
    manifests = [args.directory / mode / "manifest.json" for mode in ("baseline", "enabled")]
    if all(p.exists() for p in manifests):
        hashes = [json.loads(p.read_text())["zip_sha256"] for p in manifests]
        assert hashes[0] == hashes[1], "Baseline/enabled ZIP contents differ"
    if args.require_complete:
        sets = [{p.name for p in (args.directory / mode).glob("*.json") if p.name not in excluded}
                for mode in ("baseline", "enabled")]
        assert sets[0] == sets[1], "Baseline/enabled PDF sets differ"
    for path in sorted((args.directory / "enabled").glob("*.json")):
        if path.name in excluded:
            continue
        baseline = args.directory / "baseline" / path.name
        if not baseline.exists():
            raise SystemExit(f"Missing baseline: {baseline}")
        results.append(compare(json.loads(baseline.read_text()), json.loads(path.read_text())))
    assert results, "No comparisons found"
    report = {"compared": len(results), "changed": sum(bool(r["changes"]) for r in results),
              "failures": sum(bool(r["failures"]) for r in results), "results": results}
    (args.directory / args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "results"}))
    for r in results:
        if r["changes"] or r["failures"]:
            print(json.dumps(r, ensure_ascii=False))
    raise SystemExit(bool(report["failures"]))


if __name__ == "__main__":
    main()
