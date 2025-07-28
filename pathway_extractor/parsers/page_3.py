import re


def test_row(row):
    if len(row) > 8 or len(row) < 4:
        print(f"⚠️ Unexpected row length (page 3) ({len(row)}): {row}")
        return True
    return False


def normalize_header(header):
    """Normalize headers to lowercase and strip spaces/punctuation."""
    return re.sub(r'\W+', '', header.strip().lower() if header else '')


def parse_page_3_table(table: list) -> dict:
    results = []
    headers = []
    skill_fields = ["grammar", "listen", "read", "speak", "vocabulary", "write"]
    
    for ix, row in enumerate(table):
        if not row or all(cell is None or not str(cell).strip() for cell in row):
            continue

        if 'Total' == row[0]:
            continue 

        # Identify header row
        if ix == 0:
            print(f"Header row: {ix}: {row}")
            headers = [normalize_header(h) for h in row]
            continue

        if test_row(row):
            continue

        try:
            row_dict = dict(zip(headers, row))

            name_field = next((key for key in headers if "contactname" in key or "name" in key), None)
            if not name_field or not row_dict.get(name_field):
                print(f"⚠️ No valid name field in row: {row}")
                continue

            name = row_dict[name_field].strip()
            if not re.search(r'[A-Za-z]', name) or re.search(r'[^\w\s\-\']', name):
                continue

            skill_values = []
            for skill in skill_fields:
                matched_col = next((key for key in headers if skill in key), None)
                val = row_dict.get(matched_col) if matched_col else ''
                skill_values.append(int(val) if val and str(val).strip().isdigit() else 0)

            total_field = next((key for key in headers if "total" in key), None)
            total_val = row_dict.get(total_field) if total_field else ''
            total = int(total_val) if total_val and str(total_val).strip().isdigit() else sum(skill_values)

            results.append({
                "student_name": name,
                "skill_submissions": dict(zip(skill_fields, skill_values)),
                "total": total
            })

        except Exception as e:
            print(f"❌ Failed to parse row: {row}\nError: {e}")
            continue

    return {"page3_data": results}



# import re


# def test_row(row):
#     if len(row) > 8 or len(row) < 5:
#         print(f"⚠️ Unexpected row length (page 3) ({len(row)}): {row}")
#         return True
#     return False


# def parse_page_3_table(table: list) -> dict:
#     results = []

#     # Skip header row(s)
#     for ix, row in enumerate(table):
#         if ix == 0:
#             print(f"Header row: {ix}: {row}")
#         if (
#             not row
#             or row[0] is None
#             or all(not (cell or '').strip() for cell in row)
#             or any(keyword in (row[0] or '').lower() for keyword in ['pw_contactname', 'assignments', 'student level', 'total'])
#             or not re.search(r'[A-Za-z]', row[0])  # must have letters
#             or re.search(r'[^\w\s\-\']', row[0])    # contains junk symbols
#         ):
#             continue

#         if test_row(row):
#             continue

#         try:
#             name = row[0].strip()
#             skill_values = [(int(cell) if cell and cell.strip().isdigit() else 0) for cell in row[1:7]]
#             total = int(row[7]) if row[7] and row[7].strip().isdigit() else sum(skill_values)

#             results.append({
#                 "student_name": name,
#                 "skill_submissions": {
#                     "grammar": skill_values[0],
#                     "listen": skill_values[1],
#                     "read": skill_values[2],
#                     "speak": skill_values[3],
#                     "vocabulary": skill_values[4],
#                     "write": skill_values[5]
#                 },
#                 "total": total
#             })

#         except Exception as e:
#             print(f"❌ Failed to parse row: {row}\nError: {e}")
#             continue

#     return {"page3_data": results}
