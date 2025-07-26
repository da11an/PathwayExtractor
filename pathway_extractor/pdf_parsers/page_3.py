def parse_page_3_table(table: list) -> dict:
    results = []

    # Skip header row(s)
    for row in table:
        if not row or row[0] == 'pw_contactname' or all(not cell.strip() for cell in row):
            continue  # skip header and blank rows

        if len(row) != 8:
            print(f"⚠️ Unexpected row length ({len(row)}): {row}")
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
