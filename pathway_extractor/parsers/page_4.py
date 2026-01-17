import re

from pathway_extractor.parsers.utils import clean_value, normalize_header


def test_row(row):
    if len(row) < 7:
        print(f"⚠️ Unexpected row length (page 4) ({len(row)}): {row}")
        return True
    return False


def parse_page_4_table(table: list, headers: list, target_header: str = "pw_contactname") -> dict:
    results = []
    
    if not headers:
        print(f"⚠️  parse_page_4_table: No headers provided")
        return {"skill_scores": results}

    for row_idx, row in enumerate(table):
        # Skip title/header/empty rows
        skip_reasons = []
        if not row:
            skip_reasons.append("empty row")
        elif row[0] is None:
            skip_reasons.append("row[0] is None")
        elif all(not (cell or '').strip() for cell in row):
            skip_reasons.append("all cells empty")
        elif target_header.lower() in (row[0] or '').lower():
            skip_reasons.append(f"contains target_header '{target_header}'")
        elif 'student level' in (row[0] or '').lower():
            skip_reasons.append("contains 'student level'")
        elif 'assignments' in (row[0] or '').lower():
            skip_reasons.append("contains 'assignments'")
        elif 'indicate the criteria' in (row[0] or '').lower():
            skip_reasons.append("contains 'indicate the criteria'")
        elif not re.search(r'[A-Za-z]', row[0]):
            skip_reasons.append("no letters in row[0]")
        elif re.search(r'[^\w\s\-\'\.]', row[0]):
            skip_reasons.append("invalid characters in row[0]")
        elif 'Total' == row[0]:
            skip_reasons.append("is 'Total'")
        
        if skip_reasons:
            if row_idx < 3:  # Only print first few skipped rows to avoid spam
                print(f"   Skipping row {row_idx}: {skip_reasons[0]} - {row[0] if row and row[0] else 'N/A'}")
            continue

        if test_row(row):
            print(f"   Row {row_idx} failed test_row check: {row}")
            continue

        try:
            normalized_headers = [normalize_header(header) for header in headers]
            if len(normalized_headers) != len(row):
                print(f"   ⚠️  Row {row_idx}: Header count ({len(normalized_headers)}) != row length ({len(row)})")
                print(f"      Headers: {normalized_headers}")
                print(f"      Row: {row}")
            results.append({k:clean_value(v) for k, v in zip(normalized_headers, row)})

        except Exception as e:
            print(f"❌ Failed to parse row {row_idx}: {row}\nError: {e}")
            continue

    print(f"   ✅ parse_page_4_table: Processed {len(results)} valid rows from {len(table)} total rows")
    return {"skill_scores": results}
