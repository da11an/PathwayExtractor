import re


def test_row(row):
    return len(row) != 8


def parse_page_3_table(table: list) -> dict:
    results = []

    # Skip header row(s)
    for row in table:
        if (
            not row
            or row[0] is None
            or all(not (cell or '').strip() for cell in row)
            or any(keyword in (row[0] or '').lower() for keyword in ['pw_contactname', 'assignments', 'student level', 'total'])
            or not re.search(r'[A-Za-z]', row[0])  # must have letters
            or re.search(r'[^\w\s\-\']', row[0])    # contains junk symbols
        ):
            continue

        if test_row(row):
            print(f"⚠️ Unexpected row length (page 3) ({len(row)}): {row}")
            continue

        try:
            name = row[0].strip()
            skill_values = [(int(cell) if cell and cell.strip().isdigit() else 0) for cell in row[1:7]]
            total = int(row[7]) if row[7] and row[7].strip().isdigit() else sum(skill_values)

            results.append({
                "student_name": name,
                "skill_submissions": {
                    "grammar": skill_values[0],
                    "listen": skill_values[1],
                    "read": skill_values[2],
                    "speak": skill_values[3],
                    "vocabulary": skill_values[4],
                    "write": skill_values[5]
                },
                "total": total
            })

        except Exception as e:
            print(f"❌ Failed to parse row: {row}\nError: {e}")
            continue

    return {"page3_data": results}
