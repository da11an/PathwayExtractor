def parse_page_2_table(table: list) -> dict:
    results = []

    # Skip header row(s)
    for ix, row in enumerate(table):
        if not row or row[0] == 'pw_contactname' or all(not cell.strip() for cell in row):
            continue  # skip header and blank rows

        if len(row) < 6:
            print(f"⚠️ Unexpected row length ({len(row)}): {row}")
            continue

        try:
            name = row[0].strip()
            week_values = [(int(cell) if cell and cell.strip().isdigit() else 0) for cell in row[1:-1]]
            total = int(row[-1]) if row[-1] and row[-1].strip().isdigit() else sum(week_values)

            results.append({
                "student_name": name,
                "weekly_submissions": week_values,
                "total": total
            })

        except Exception as e:
            print(f"❌ Failed to parse row: {row}\nError: {e}")
            continue

    results = results[1:]

    return {"page2_data": results}
