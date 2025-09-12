import re

from pathway_extractor.parsers.utils import clean_value, normalize_header


def test_row(row):
    if len(row) < 7:
        print(f"⚠️ Unexpected row length (page 4) ({len(row)}): {row}")
        return True
    return False


def parse_page_4_table(table: list, headers: list) -> dict:
    results = []

    for row in table:
        # Skip title/header/empty rows
        if (
            not row
            or row[0] is None
            or all(not (cell or '').strip() for cell in row)
            or 'pw_contactname' in (row[0] or '').lower()
            or 'student level' in (row[0] or '').lower()
            or 'assignments' in (row[0] or '').lower()
            or 'indicate the criteria' in (row[0] or '').lower()
            or not re.search(r'[A-Za-z]', row[0])
            or re.search(r'[^\w\s\-\'\.]', row[0])
            or 'Total' == row[0]
        ):
            continue

        if test_row(row):
            continue

        try:
            normalized_headers = [normalize_header(header) for header in headers]
            results.append({k:clean_value(v) for k, v in zip(normalized_headers, row)})

        except Exception as e:
            print(f"❌ Failed to parse row: {row}\nError: {e}")
            continue

    return {"skill_scores": results}
