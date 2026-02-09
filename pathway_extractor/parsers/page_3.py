import re

from pathway_extractor.parsers.utils import clean_value, normalize_header, merge_wrapped_name_rows


def test_row(row):
    if len(row) > 8 or len(row) < 3:
        print(f"⚠️ Unexpected row length (page 3) ({len(row)}): {row}")
        return True
    return False


def parse_page_3_table(table: list, headers: list, target_header: str = "pw_contactname", known_names: set = None) -> dict:
    # Merge wrapped name rows before processing, using known names from page 2 for validation
    table = merge_wrapped_name_rows(table, known_names=known_names)
    
    results = []
    normalized_headers = [normalize_header(header) for header in headers]
    # Normalize the target_header for comparison
    normalized_target = normalize_header(target_header)
    # Map first column to student_name if it matches target or is a known name column variant
    if normalized_headers and (normalized_headers[0] == normalized_target or normalized_headers[0] == "ec3enrollmentstatus"):
        normalized_headers[0] = "student_name"

    skill_fields = ["grammar", "listen", "read", "speak", "vocabulary", "write"]
    
    for ix, row in enumerate(table):
        if not row or all(cell is None or not str(cell).strip() for cell in row):
            continue

        if 'Total' == row[0]:
            continue 

        if test_row(row):
            continue

        try:
            row_dict = dict(zip(normalized_headers, row))

            results.append({
                k:clean_value(v) for k, v in zip(normalized_headers, row)
            })

        except Exception as e:
            print(f"❌ Failed to parse row: {row}\nError: {e}")
            continue

    return {"submissions_by_skill": results}
