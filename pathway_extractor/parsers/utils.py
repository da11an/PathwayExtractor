import re
from collections import defaultdict


def normalize_header(header):
    """Normalize headers to lowercase and strip spaces/punctuation."""
    normalized = re.sub(r'\W+', '', header.strip().lower() if header else '')
    substitutions = {
        "pw_contactname": "student_name",
        "name": "student_name",  # Map 'name' to 'student_name' for consistency
        "ec3enrollmentstatus": "student_name",  # Map 'EC3EnrollmentStatus' to 'student_name'
        "allskillscompleted": "student_name",  # Map 'AllSkillsCompleted' to 'student_name'
        "grammar": "grammar",
        "vocab": "vocabulary",
        "read": "reading",
        "write": "writing",
        "speak": "speaking",
        "listen": "listening",
    }
    return substitutions.get(normalized, normalized)


def _is_empty_cell(cell):
    """
    Check if a cell is effectively empty (None, empty string, 0, whitespace, or common placeholders).
    This helps detect wrapped name rows where other columns might be 0, "", "-", "N/A", etc. instead of None.
    """
    if cell is None:
        return True
    if isinstance(cell, str):
        stripped = cell.strip()
        # Consider empty, "0", "-", "N/A", "n/a", "NA", "na" as empty
        return stripped == "" or stripped in ("0", "-", "N/A", "n/a", "NA", "na", "null", "NULL")
    if isinstance(cell, (int, float)):
        return cell == 0
    return False


def _normalize_name_for_comparison(name: str) -> str:
    """Normalize a name for comparison by lowercasing and removing extra whitespace."""
    return " ".join(name.lower().split())


def _is_prefix_of_known_name(text: str, normalized_known_names: set) -> bool:
    """Check if text is a prefix of any known name (normalized comparison)."""
    text_norm = _normalize_name_for_comparison(text)
    return any(known.startswith(text_norm) for known in normalized_known_names)


def _find_last_name_row_index(merged_table: list) -> int:
    """Find the index of the last row in merged_table that has a name in column 0.
    Skips past empty rows to find the actual previous data row."""
    for idx in range(len(merged_table) - 1, -1, -1):
        row = merged_table[idx]
        if row and len(row) > 0 and row[0] is not None and str(row[0]).strip():
            return idx
    return -1


def merge_wrapped_name_rows(table: list, known_names: set = None) -> list:
    """
    Merge rows where a long name has wrapped across multiple rows.

    When a name is very long, it may wrap to a new row where:
    - First column contains the name continuation (text)
    - All other columns are None, empty, or 0

    This function detects such rows and merges them with the previous row's name.
    This must be called BEFORE clean_value() converts None to 0, so we can detect
    the None values in other columns. However, it also handles cases where cells
    are already 0 or empty strings.

    Cross-page validation: If known_names is provided, uses prefix matching to
    validate merges — the merged name must be a prefix of a known name, and
    the continuation fragment alone must NOT be a complete known name.

    Args:
        table: List of rows, where each row is a list of cell values
        known_names: Optional set of normalized names from page 2 (first table) to use
                    for validation. If a name already matches a known name, don't merge.

    Returns:
        List of rows with wrapped name rows merged into previous rows
    """
    if not table:
        return table

    # Pre-filter: remove completely empty rows (extraction artifacts from Y-position gaps
    # in wrapped names). These block merge logic by sitting between a data row and its
    # name continuation. Parsers skip empty rows anyway.
    filtered_table = []
    for row in table:
        if not row:
            continue
        if all(_is_empty_cell(cell) for cell in row):
            continue
        filtered_table.append(row)
    table = filtered_table

    # Normalize known names for comparison
    normalized_known_names = set()
    if known_names:
        normalized_known_names = {_normalize_name_for_comparison(name) for name in known_names}

    merged_table = []

    for i, row in enumerate(table):
        first_col = row[0] if len(row) > 0 else None
        other_cols = row[1:] if len(row) > 1 else []

        # Check if first column has meaningful text (not empty, not just "0")
        has_first_col_text = (
            first_col is not None
            and not _is_empty_cell(first_col)
            and str(first_col).strip() != ""
        )

        if not has_first_col_text:
            merged_table.append(row)
            continue

        # Check if all other columns are effectively empty
        all_others_empty = all(_is_empty_cell(cell) for cell in other_cols)

        # Cross-page validation: If this row's name already perfectly matches a known name,
        # don't merge it (it's likely a complete name, not a continuation)
        if normalized_known_names:
            current_name_normalized = _normalize_name_for_comparison(str(first_col))
            if current_name_normalized in normalized_known_names:
                merged_table.append(row)
                continue

        # If this looks like a name continuation row AND we have a previous row to merge with
        if all_others_empty and len(merged_table) > 0:
            # Find the last row with a name (skip past any empty rows)
            prev_idx = _find_last_name_row_index(merged_table)
            if prev_idx >= 0:
                prev_row = merged_table[prev_idx]
                prev_first_col = str(prev_row[0]).strip()
                prev_looks_like_name = (
                    len(prev_first_col) > 0
                    and any(c.isalpha() for c in prev_first_col)
                    and prev_first_col.lower() not in ('total', 'name', 'pw_contactname')
                )

                if prev_looks_like_name:
                    continuation = str(first_col).strip()
                    merged_name = f"{prev_first_col} {continuation}".strip()

                    if normalized_known_names:
                        continuation_normalized = _normalize_name_for_comparison(continuation)
                        merged_name_normalized = _normalize_name_for_comparison(merged_name)

                        # If the continuation alone is a known name, don't merge (separate person)
                        if continuation_normalized in normalized_known_names:
                            merged_table.append(row)
                            continue

                        # Validate: merged name must be a prefix of (or match) a known name.
                        # This prevents merging "Sanchez" into a previous unrelated student.
                        if not _is_prefix_of_known_name(merged_name, normalized_known_names):
                            # Merged name doesn't match any known name — don't merge.
                            # This fragment might be the start of a new wrapped name.
                            merged_table.append(row)
                            continue

                    # Merge: update the target row's first column
                    merged_table[prev_idx] = [merged_name] + list(prev_row[1:])
                    continue

        # Not a continuation row, add it as-is
        merged_table.append(row)

    return merged_table


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
        # Try both 'student_name' and 'name' for compatibility (normalize_header should handle this, but keep fallback)
        name = item.pop("student_name", None) or item.pop("name", None)
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
