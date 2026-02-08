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


def merge_wrapped_name_rows(table: list) -> list:
    """
    Merge rows where a long name has wrapped across multiple rows.
    
    When a name is very long, it may wrap to a new row where:
    - First column contains the name continuation (text)
    - All other columns are None or empty
    
    This function detects such rows and merges them with the previous row's name.
    This must be called BEFORE clean_value() converts None to 0, so we can detect
    the None values in other columns.
    
    Args:
        table: List of rows, where each row is a list of cell values
        
    Returns:
        List of rows with wrapped name rows merged into previous rows
    """
    if not table:
        return table
    
    merged_table = []
    
    for i, row in enumerate(table):
        if not row:
            merged_table.append(row)
            continue
        
        # Check if this row is a name continuation:
        # - First column has text (not None, not empty after strip)
        # - All other columns are None or empty/whitespace
        first_col = row[0] if len(row) > 0 else None
        other_cols = row[1:] if len(row) > 1 else []
        
        # Check if first column has text
        has_first_col_text = (
            first_col is not None 
            and str(first_col).strip() != ""
        )
        
        # Check if all other columns are None/empty
        # This is the key check - we need to detect None before clean_value converts it to 0
        all_others_empty = all(
            cell is None 
            or (isinstance(cell, str) and cell.strip() == "") 
            or cell == ""
            for cell in other_cols
        )
        
        # If this looks like a name continuation row AND we have a previous row to merge with
        if has_first_col_text and all_others_empty and len(merged_table) > 0:
            # Merge with previous row's first column
            prev_row = merged_table[-1]
            if prev_row and len(prev_row) > 0 and prev_row[0] is not None:
                # Append the continuation text to the previous row's name
                prev_name = str(prev_row[0]).strip()
                continuation = str(first_col).strip()
                # Join with a space
                merged_name = f"{prev_name} {continuation}".strip()
                # Update the previous row's first column
                merged_table[-1] = [merged_name] + list(prev_row[1:])
                # Skip adding this row (it's been merged)
                continue
            # If previous row doesn't have a name, treat this as a new row (edge case)
        
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
