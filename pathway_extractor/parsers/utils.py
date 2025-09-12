import re
from collections import defaultdict


def normalize_header(header):
    """Normalize headers to lowercase and strip spaces/punctuation."""
    normalized = re.sub(r'\W+', '', header.strip().lower() if header else '')
    substitutions = {
        "pw_contactname": "student_name",
        "grammar": "grammar",
        "vocab": "vocabulary",
        "read": "reading",
        "write": "writing",
        "speak": "speaking",
        "listen": "listening",
    }
    return substitutions.get(normalized, normalized)


def clean_value(value):
    if value is None or value == "":
        return 0
    elif value.strip().lstrip('-').isdigit():
        return int(value)
    else:
        return value


def invert_student_data(record):
    student_data = defaultdict(dict)

    # Weekly submissions
    for item in record.get("weekly_submissions", []):
        name = item.pop("student_name", None)
        if name:
            student_data[name]["weekly_submissions"] = item

    # Submissions by skill
    for item in record.get("submissions_by_skill", []):
        name = item.pop("student_name", None)
        if name:
            student_data[name]["submissions_by_skill"] = item

    # Skill scores
    for item in record.get("skill_scores", []):
        name = item.pop("student_name", None)
        if name:
            student_data[name]["skill_scores"] = item

    # if not student_data:
        # raise ValueError("No students found in input data.")

    return {
        "file": record.get("file"),
        "pdf_size": record.get("pdf_size"),
        "class_info": record.get("class_info"),
        "students": student_data
    }
