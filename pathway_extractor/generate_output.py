from collections import defaultdict

def merge_student_data(page2_data, page3_data, page4_data):
    merged = defaultdict(dict)

    # Merge weekly submissions from page 2
    for entry in page2_data:
        name = entry.get("student_name")
        if name:
            merged[name]["student_name"] = name
            merged[name]["weekly_submissions"] = entry.get("weekly_submissions", [])
            merged[name]["total"] = entry.get("total")

    # Merge skill units from page 3
    for entry in page3_data:
        name = entry.get("student_name")
        if name:
            merged[name]["student_name"] = name
            merged[name]["skill_submissions"] = entry.get("skill_submissions", {})
            merged[name]["total"] = entry.get("total")  # optional; could validate vs. page2 total

    # Merge skill levels from page 4
    for entry in page4_data:
        name = entry.get("student_name")
        if name:
            merged[name]["student_name"] = name
            merged[name]["skill_levels"] = entry.get("skill_levels", {})

    return list(merged.values())


def summarize_student(student: dict) -> dict:
    name = student["student_name"]

    # Skill keys should match across levels and units
    skill_keys = ["grammar", "listen", "read", "speak", "vocabulary", "write"]

    levels = student.get("skill_levels", {})
    units = student.get("skill_submissions", {})

    # Fallback: use 0 if data is missing
    level_data = {k: levels.get(k, 0) for k in skill_keys}
    unit_data = {k: units.get(k, 0) for k in skill_keys}

    total_units = sum(unit_data.values())
    avg_units = round(total_units / 7, 1) # TODO: denominator isn't going to be fixed at 7. Will change

    return {
        "student_name": name,
        "level": level_data,
        "units": unit_data,
        "average_units_per_week": avg_units,
        "message": f"😊 Good morning, {name.split()[0]}! Here is the most recent update on units you have completed in the English learning app. If you have a question about the chart and what it means please pick up your phone and call me."
    }

# python pathway_extractor\tests\test_output.py test_output.jsonl --output-jsonl student_summaries.jsonl
