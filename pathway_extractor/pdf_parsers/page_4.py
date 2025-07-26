def parse_page_4_table(table: list) -> dict:
    results = []

    for row in table:
        # Skip title/header/empty rows
        if (
            not row
            or row[0] is None
            or all(not (cell or '').strip() for cell in row)
            or 'pw_contactname' in (row[0] or '').lower()
            or 'student level' in (row[0] or '').lower()
        ):
            continue

        if len(row) < 7:
            print(f"⚠️ Unexpected row length ({len(row)}): {row}")
            continue

        try:
            name = row[0].strip()
            skills = [(int(cell) if cell and cell.strip().lstrip('-').isdigit() else 0) for cell in row[1:7]]

            results.append({
                "student_name": name,
                "skill_levels": {
                    "grammar": skills[0],
                    "listen": skills[1],
                    "read": skills[2],
                    "speak": skills[3],
                    "vocab": skills[4],
                    "write": skills[5]
                }
            })

        except Exception as e:
            print(f"❌ Failed to parse row: {row}\nError: {e}")
            continue

    return {"page4_data": results}
