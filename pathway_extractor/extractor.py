import re
import io
import json
from zipfile import ZipFile
import pdfplumber
from tqdm import tqdm
import argparse

from pathway_extractor.parsers.page_2 import parse_page_2_table, test_row as test_row_page_2
from pathway_extractor.parsers.page_3 import parse_page_3_table, test_row as test_row_page_3
from pathway_extractor.parsers.page_4 import parse_page_4_table, test_row as test_row_page_4
from pathway_extractor.parsers.filename import parse_filename

PAGES_TO_GRAB = [1, 2, 3]  # zero-based index for pages 2,3,4


def find_correct_crop(page, target="pw_contactname", start_top=177, max_shift=150, delta=20):
    """
    Iteratively adjust the top crop to find where the first word matches the expected header.
    Returns the cropped page or None if not found.

    This greatly improves the accuracy of the table extraction by preventing the header from
    confusing where the column breaks are.
    """
    shifts = [0]
    # Alternate up/down shifts: [0, 20, -20, 40, -40, 60, -60, ...]
    for i in range(1, max_shift // delta + 1):
        shifts.extend([i * delta, -i * delta])

    for shift in shifts:
        top = start_top + shift
        if top < 0:
            continue
        cropped = page.within_bbox((0, top, page.width, page.height))
        text = cropped.extract_text()
        if not text:
            continue
        first_word = text.strip().split()[0]
        if first_word == target:
            return cropped, top

    return None  # target not found


def split_page_header_body(page, top_crop=177, header_height=25):
    """
    Crops a page into two: one for header row, one for the table body.
    Returns (header_page, body_page)
    """
    header_bbox = (0, top_crop, page.width, top_crop + header_height)
    body_bbox = (0, top_crop + header_height, page.width, page.height)

    header_page = page.within_bbox(header_bbox)
    body_page = page.within_bbox(body_bbox)

    return header_page, body_page


def get_header_labels_and_positions(page, y_tolerance=4):
    """
    Extracts a single header row from a cropped page using word positions.
    Groups words by y-position, sorts by x, and returns [(label, x0)] for each header cell.

    Weakness: First header is left aligned, others are right aligned, so if text in column is
    wider than header, it may be split into multiple columns.
    """
    words = page.extract_words()

    if not words:
        return []

    # Find the top-most line of text (lowest y0)
    min_top = min(w["top"] for w in words)
    header_words = [w for w in words if abs(w["top"] - min_top) <= y_tolerance]

    # Sort by x0
    header_words.sort(key=lambda w: w["x0"])

    # Group into headers based on spacing
    labels = []
    current_label = ""
    current_x0 = None
    spacing_threshold = 5  # adjust if headers are spaced out or tight

    for i, w in enumerate(header_words):
        text = w["text"]
        x0 = w["x0"]
        x1 = w["x1"]

        if current_label == "":
            current_label = text
            current_x0 = x0
            current_x1 = x1
        else:
            prev_x1 = header_words[i - 1]["x1"]
            gap = x0 - prev_x1
            if gap <= spacing_threshold:
                current_label += " " + text
            else:
                labels.append((current_label.strip(), current_x0, current_x1))
                current_label = text
                current_x0 = x0
                current_x1 = x1

    if current_label:
        labels.append((current_label.strip(), current_x0, current_x1))

    return labels


def extract_largest_table(page, table_settings=None, idx=None):
    """
    Extract the largest table from a page, prioritizing by row count then column count.
    
    Args:
        page: pdfplumber page object
        table_settings: Settings for table extraction
        
    Returns:
        List of rows (table data) or empty list if no tables found
    """
    if table_settings is None:
        table_settings = {
            "vertical_strategy": "text",
            "horizontal_strategy": "text"
        }

    # Extract all tables from the page
    tables = page.extract_tables(table_settings=table_settings)
    page.to_image(resolution=200).debug_tablefinder(table_settings=table_settings).save(f"debug_page{idx}.png")
    
    if not tables:
        return []
    
    # Find the largest table by row count, then by column count
    largest_table = max(tables, key=lambda table: (
        len(table) if table else 0,  # Row count
        max(len(row) for row in table) if table and table[0] else 0  # Max column count
    ))
    
    return largest_table or []


def parse_record(file_name: str, page_tables: dict, page_headers: dict) -> dict:
    parsed = {
        "file": file_name,
        **parse_filename(file_name),
        **parse_page_2_table(page_tables.get("page2_text", []), page_headers.get("page2_text", [])),
        **parse_page_3_table(page_tables.get("page3_text", []), page_headers.get("page3_text", [])),
        **parse_page_4_table(page_tables.get("page4_text", []), page_headers.get("page4_text", [])),
    }
    return parsed


def extract_records_from_zip(zip_path: str, max_files: int = None, filename_filter: str = None) -> list:
    """Process all PDFs in a zip file and return list of extracted records."""
    records = []
    with ZipFile(zip_path, "r") as zf:
        pdf_names = [
            n for n in zf.namelist()
            if n.lower().endswith(".pdf") and (filename_filter is None or filename_filter in n)
        ]

        # Optionally limit the number of files
        if max_files is not None:
            pdf_names = pdf_names[:max_files]

        for name in tqdm(pdf_names, desc="Processing PDFs"):
            try:
                with zf.open(name) as f:
                    data = f.read()
                with pdfplumber.open(io.BytesIO(data)) as pdf:
                    page_tables = {}
                    page_headers = {}
                    for idx, label, row_test in zip(
                            PAGES_TO_GRAB,
                            ["page2_text", "page3_text", "page4_text"],
                            [test_row_page_2, test_row_page_3, test_row_page_4]
                        ):
                        print("idx", idx, "len(pdf.pages)", len(pdf.pages), "label", label)
                        labels = []
                        if idx < len(pdf.pages):
                            page, top_crop = find_correct_crop(pdf.pages[idx])
                            header_page, body_page = split_page_header_body(page, top_crop=top_crop)

                            # Debugging
                            page.to_image(resolution=150).save(f"page_{idx}.png")
                            header_page.to_image(resolution=150).save(f"header_page_{idx}.png")

                            if label in ["page4_text", "page3_text", "page2_text"]:
                                header_labels_and_positions = get_header_labels_and_positions(header_page)
                                labels, x0_positions, x1_positions = zip(*[(label, x0, x1) for label, x0, x1 in header_labels_and_positions])
                                header_x_positions = x0_positions[:2] + x1_positions[1:]
                                # Ensure minimum width for second column
                                minimum_column_width = 17
                                if len(header_x_positions) >= 3:
                                    col2_width = header_x_positions[2] - header_x_positions[1]
                                    if col2_width < minimum_column_width:
                                        header_x_positions = list(header_x_positions)  # Convert to list for modification
                                        header_x_positions[1] = header_x_positions[2] - minimum_column_width

                                table_settings = {
                                    "vertical_strategy": "explicit",
                                    "horizontal_strategy": "text",
                                    "explicit_vertical_lines": header_x_positions,
                                }

                                table = extract_largest_table(body_page, table_settings=table_settings, idx=idx)
                            else:
                                table = extract_largest_table(page, table_settings=None, idx=idx)
                            print("name", name)
                            print("label", label)
                            # [row_test(row) for row in table]
                        else:
                            table = []
                            labels = []
                        page_tables[label] = table
                        page_headers[label] = labels

                    rec = parse_record(name, page_tables, page_headers)
                    records.append(rec)

            except Exception as e:
                err_obj = {"file": name, "error": str(e)}
                records.append(err_obj)

    return records


def write_records_to_jsonl(records: list, jsonl_out: str):
    """Write a list of records to a JSONL file."""
    with open(jsonl_out, "w", encoding="utf-8") as jsonl_f:
        for rec in records:
            jsonl_f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def process_zip(zip_path: str, jsonl_out: str, max_files: int = None, filename_filter: str = None):
    records = extract_records_from_zip(zip_path, max_files, filename_filter)
    write_records_to_jsonl(records, jsonl_out)
    print(f"Done. JSONL output -> {jsonl_out}")
    args = parser.parse_args()

    process_zip(args.zip_path, args.jsonl_out, filename_filter=args.filename_filter)


if __name__ == "__main__":
    main()
