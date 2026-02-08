import re

from pathway_extractor.parsers.utils import clean_value, merge_wrapped_name_rows


def test_row(row):
    if len(row) < 3 or len(row) > 9:
        print(f"⚠️ Unexpected row length (page 2) ({len(row)}): {row}")
        return True
    return False


def parse_page_2_table(table: list, headers: list, target_header: str = "pw_contactname") -> dict:
    # Merge wrapped name rows before processing
    table = merge_wrapped_name_rows(table)
    
    results = []

    # Skip header row(s)
    for row in table:
        if not row or (row[0] and str(row[0]).strip().lower() == target_header.lower()) or all(not cell.strip() for cell in row):
            continue  # skip header and blank rows

        # Skip junk names (e.g., , �, symbols)
        if not re.search(r'[A-Za-z]', row[0]) or re.search(r'[^\w\s\-\'\.]', row[0]):
            continue  # skip weird row

        # Skip junk names (e.g., , �, symbols)
        if 'Assignments' in row[0]:
            continue  # skip header weird row

        if 'Total' == row[0]:
            continue 

        if test_row(row):
            continue

        try:
            name = row[0].strip()
            week_values = [(int(cell) if cell and cell.strip().isdigit() else 0) for cell in row[1:-1]]
            total = int(row[-1]) if row[-1] and row[-1].strip().isdigit() else sum(week_values)
            keys = ["student_name"] + [f"week_{i}" for i in range(1, len(week_values) + 1)] + ["total"]

            results.append({
                k:clean_value(v) for k, v in zip(keys, row)
            })

        except Exception as e:
            print(f"❌ Failed to parse row: {row}\nError: {e}")
            continue

    # results = results[1:]

    return {"weekly_submissions": results}
