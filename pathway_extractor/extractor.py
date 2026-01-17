import re
import io
import json
from zipfile import ZipFile
import pdfplumber
from tqdm import tqdm
import argparse
from typing import Optional

from pathway_extractor.parsers.filename import parse_filename
from pathway_extractor.config_loader import ExtractionConfig, load_config


def find_correct_crop(page, target="pw_contactname", start_top=177, max_shift=150, delta=20, left_bound=None, right_bound=None):
    """
    Iteratively adjust the top crop to find where the first word matches the expected header.
    Returns the cropped page or None if not found.

    This greatly improves the accuracy of the table extraction by preventing the header from
    confusing where the column breaks are.
    
    Args:
        page: pdfplumber page object
        target: First word to search for
        start_top: Initial Y position to start searching
        max_shift: Maximum pixels to shift up/down
        delta: Step size for shifting
        left_bound: Left X boundary (None = 0, use full page)
        right_bound: Right X boundary (None = page.width, use full page)
    """
    # Use full page width if bounds not specified
    left = left_bound if left_bound is not None else 0
    right = right_bound if right_bound is not None else page.width
    
    shifts = [0]
    # Alternate up/down shifts: [0, 20, -20, 40, -40, 60, -60, ...]
    for i in range(1, max_shift // delta + 1):
        shifts.extend([i * delta, -i * delta])

    for shift in shifts:
        top = start_top + shift
        if top < 0:
            continue
        cropped = page.within_bbox((left, top, right, page.height))
        text = cropped.extract_text()
        if not text:
            continue
        first_word = text.strip().split()[0]
        if first_word == target:
            # Return the cropped page and the top position
            # Note: top is the Y position in the original page coordinates
            return cropped, top

    return None, None  # target not found


def split_page_header_body(page, top_crop=0, header_height=25, left_bound=None, right_bound=None):
    """
    Crops a page into two: one for header row, one for the table body.
    Returns (header_page, body_page)
    
    Args:
        page: pdfplumber page object (already cropped horizontally and vertically)
        top_crop: Y position where table starts (relative to the cropped page, typically 0)
        header_height: Height of the header row
        left_bound: Left X boundary (None = 0, use full cropped page width)
        right_bound: Right X boundary (None = page.width, use full cropped page width)
    """
    # Get the page's bounding box to work with its coordinate system
    page_bbox = page.bbox  # (x0, y0, x1, y1) in the cropped page's coordinates
    page_left = page_bbox[0]
    page_top = page_bbox[1]
    page_right = page_bbox[2]
    page_bottom = page_bbox[3]
    page_width = page_right - page_left
    page_height = page_bottom - page_top
    
    # Use full cropped page width if bounds not specified
    left = left_bound if left_bound is not None else page_left
    right = right_bound if right_bound is not None else page_right
    
    # top_crop is relative to the cropped page, so add it to the page's top
    header_top = page_top + top_crop
    header_bottom = header_top + header_height
    body_top = header_bottom
    body_bottom = page_bottom
    
    header_bbox = (left, header_top, right, header_bottom)
    body_bbox = (left, body_top, right, body_bottom)

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


def extract_largest_table(page, table_settings=None, label=None, debug=False):
    """
    Extract the largest table from a page, prioritizing by row count then column count.
    
    Args:
        page: pdfplumber page object
        table_settings: Settings for table extraction
        label: Label for debug image filename (optional)
        debug: Whether to save debug images
        
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
    if debug and label is not None:
        debug_tablefinder_filename = f"debug_tablefinder_{label}.png"
        page.to_image(resolution=200).debug_tablefinder(table_settings=table_settings).save(debug_tablefinder_filename)
        print(f"   💾 Saved table finder debug image: {debug_tablefinder_filename}")
    
    if not tables:
        return []
    
    # Find the largest table by row count, then by column count
    largest_table = max(tables, key=lambda table: (
        len(table) if table else 0,  # Row count
        max(len(row) for row in table) if table and table[0] else 0  # Max column count
    ))
    
    return largest_table or []


def parse_record(file_name: str, page_tables: dict, page_headers: dict, pdf_size: float, config: ExtractionConfig) -> dict:
    """Parse extracted tables into a record using configured parsers."""
    parsed = {
        "file": file_name,
        **parse_filename(file_name),
        "pdf_size": pdf_size,
    }
    
    # Apply parsers for each configured page
    for page_config in config.get_page_configs():
        label = page_config.label
        parser_func = page_config.get_parser_function()
        table_data = page_tables.get(label, [])
        headers = page_headers.get(label, [])
        
        # Debug output
        print(f"🔍 Parsing {label}: {len(table_data)} rows, {len(headers)} headers")
        if table_data:
            print(f"   First row: {table_data[0]}")
        if headers:
            print(f"   Headers: {headers}")
        
        # Pass the target_header to the parser function
        result = parser_func(table_data, headers, target_header=page_config.target_header)
        print(f"   Parser result keys: {list(result.keys())}")
        for key, value in result.items():
            if isinstance(value, list):
                print(f"   {key}: {len(value)} items")
            else:
                print(f"   {key}: {value}")
        parsed.update(result)
    
    return parsed


def extract_records_from_zip(
    zip_path: str, 
    max_files: int = None, 
    filename_filter: str = None, 
    debug: bool = True,
    config: Optional[ExtractionConfig] = None
) -> list:
    """
    Process all PDFs in a zip file and return list of extracted records.
    
    Args:
        zip_path: Path to zip file containing PDFs
        max_files: Maximum number of files to process (None for all)
        filename_filter: Filter PDFs by filename substring (None for all)
        debug: Enable debug output
        config: ExtractionConfig object. If None, loads default config.
    
    Returns:
        List of extracted records
    """
    if config is None:
        config = load_config()
    
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
                # Get size of the individual PDF file within the zip
                pdf_size = zf.getinfo(name).file_size
                if debug:
                    print("pdf_size", pdf_size)

                with zf.open(name) as f:
                    data = f.read()
                with pdfplumber.open(io.BytesIO(data)) as pdf:
                    page_tables = {}
                    page_headers = {}
                    
                    # Process each configured page
                    page_configs = config.get_page_configs()
                    if debug:
                        print(f"\n🔧 Processing {len(page_configs)} page configuration(s)")
                        config_labels = [pc.label for pc in page_configs]
                        print(f"   Config labels: {config_labels}")
                    
                    for config_num, page_config in enumerate(page_configs, 1):
                        try:
                            idx = page_config.page_index
                            label = page_config.label
                            
                            if debug:
                                print(f"\n📄 [{config_num}/{len(page_configs)}] Processing page {idx} (label: {label})")
                                print(f"   PDF has {len(pdf.pages)} pages")
                                if page_config.left_bound is not None or page_config.right_bound is not None:
                                    left = page_config.left_bound if page_config.left_bound is not None else 0
                                    right = page_config.right_bound if page_config.right_bound is not None else "page.width"
                                    print(f"   Horizontal bounds: left={left}, right={right}")
                            
                            labels = []
                            if idx < len(pdf.pages):
                                original_page = pdf.pages[idx]
                                
                                # Always print page dimensions - useful for configuration
                                print(f"   Page {idx} dimensions: {original_page.width:.1f} x {original_page.height:.1f} points")
                                print(f"   Searching for target header: '{page_config.target_header}'")
                                
                                # Save original full page for reference (only once per page index, but include label for uniqueness)
                                if debug:
                                    debug_original_filename = f"debug_original_{label}.png"
                                    original_page.to_image(resolution=150).save(debug_original_filename)
                                    print(f"   💾 Saved original full page: {debug_original_filename}")
                                
                                # Save horizontally cropped page if bounds are set
                                if debug and (page_config.left_bound is not None or page_config.right_bound is not None):
                                    left = page_config.left_bound if page_config.left_bound is not None else 0
                                    right = page_config.right_bound if page_config.right_bound is not None else original_page.width
                                    horizontally_cropped = original_page.within_bbox((left, 0, right, original_page.height))
                                    debug_horizontal_filename = f"debug_horizontal_crop_{label}_left{int(left)}_right{int(right)}.png"
                                    horizontally_cropped.to_image(resolution=150).save(debug_horizontal_filename)
                                    print(f"   💾 Saved horizontally cropped page: {debug_horizontal_filename}")
                                
                                # Use config values for crop finding with horizontal bounds
                                page, top_crop_original = find_correct_crop(
                                    original_page,
                                    target=page_config.target_header,
                                    start_top=page_config.start_top,
                                    max_shift=page_config.max_shift,
                                    delta=page_config.delta,
                                    left_bound=page_config.left_bound,
                                    right_bound=page_config.right_bound
                                )
                                
                                if page is None:
                                    if debug:
                                        print(f"⚠️  Warning: Could not find target header '{page_config.target_header}' on page {idx}")
                                        # Still save debug images even when crop fails to help diagnose
                                        left = page_config.left_bound if page_config.left_bound is not None else 0
                                        right = page_config.right_bound if page_config.right_bound is not None else original_page.width
                                        failed_crop = original_page.within_bbox((left, page_config.start_top, right, original_page.height))
                                        debug_failed_filename = f"debug_failed_crop_{label}_start{int(page_config.start_top)}.png"
                                        failed_crop.to_image(resolution=150).save(debug_failed_filename)
                                        print(f"   💾 Saved failed crop attempt: {debug_failed_filename}")
                                    table = []
                                    labels = []
                                else:
                                    # Save the cropped page at top_crop_original for inspection
                                    if debug:
                                        # Recreate the exact crop that was found for inspection
                                        left = page_config.left_bound if page_config.left_bound is not None else 0
                                        right = page_config.right_bound if page_config.right_bound is not None else original_page.width
                                        cropped_for_inspection = original_page.within_bbox((left, top_crop_original, right, original_page.height))
                                        debug_cropped_filename = f"debug_cropped_{label}_top{int(top_crop_original)}.png"
                                        cropped_for_inspection.to_image(resolution=150).save(debug_cropped_filename)
                                        print(f"   💾 Saved cropped page at top={top_crop_original:.1f}: {debug_cropped_filename}")
                                    
                                    # The page returned by find_correct_crop is cropped starting from top_crop_original
                                    # So within the cropped page, the header is at Y=0 (or close to it)
                                    # We need to adjust top_crop to be relative to the cropped page
                                    # Since the page is cropped from top_crop_original, the header should be at Y=0
                                    top_crop_in_cropped_page = 0
                                    
                                    # Note: page is already cropped horizontally and vertically by find_correct_crop
                                    # So we pass None for bounds and use top_crop_in_cropped_page
                                    header_page, body_page = split_page_header_body(
                                        page, 
                                        top_crop=top_crop_in_cropped_page,
                                        header_height=page_config.header_height,
                                        left_bound=None,  # Page already cropped horizontally
                                        right_bound=None  # Page already cropped horizontally
                                    )

                                    # Debugging - save all crop stages
                                    if debug:
                                        debug_raw_filename = f"debug_raw_{label}.png"
                                        debug_header_filename = f"debug_header_{label}.png"
                                        debug_body_filename = f"debug_body_{label}.png"
                                        page.to_image(resolution=150).save(debug_raw_filename)
                                        header_page.to_image(resolution=150).save(debug_header_filename)
                                        body_page.to_image(resolution=150).save(debug_body_filename)
                                        print(f"   💾 Saved crop stages: {debug_raw_filename}, {debug_header_filename}, {debug_body_filename}")

                                    if page_config.use_explicit_vertical_lines:
                                        header_labels_and_positions = get_header_labels_and_positions(header_page)
                                        if header_labels_and_positions:
                                            labels, x0_positions, x1_positions = zip(*[(label, x0, x1) for label, x0, x1 in header_labels_and_positions])
                                            header_x_positions = x0_positions[:2] + x1_positions[1:]
                                            # Ensure minimum width for second column
                                            if len(header_x_positions) >= 3:
                                                col2_width = header_x_positions[2] - header_x_positions[1]
                                                if col2_width < page_config.minimum_column_width:
                                                    header_x_positions = list(header_x_positions)  # Convert to list for modification
                                                    header_x_positions[1] = header_x_positions[2] - page_config.minimum_column_width

                                            table_settings = {
                                                "vertical_strategy": "explicit",
                                                "horizontal_strategy": "text",
                                                "explicit_vertical_lines": header_x_positions,
                                            }
                                            table = extract_largest_table(body_page, table_settings=table_settings, label=label, debug=debug)
                                        else:
                                            # No headers found, fall back to text-based extraction
                                            table = extract_largest_table(body_page, table_settings=None, label=label, debug=debug)
                                    else:
                                        table = extract_largest_table(body_page, table_settings=None, label=label, debug=debug)
                                    
                                    if debug:
                                        print("name", name)
                                        print("label", label)
                            else:
                                if debug:
                                    print(f"   ⚠️  Skipping: Page index {idx} is out of range (PDF has {len(pdf.pages)} pages, indices 0-{len(pdf.pages)-1})")
                                    # Still save a placeholder debug image to show this config was processed
                                    try:
                                        # Try to get the last available page as a reference
                                        if len(pdf.pages) > 0:
                                            ref_page = pdf.pages[-1]
                                            debug_skipped_filename = f"debug_skipped_{label}_page{idx}_not_found.png"
                                            ref_page.to_image(resolution=150).save(debug_skipped_filename)
                                            print(f"   💾 Saved skipped page indicator: {debug_skipped_filename}")
                                    except Exception as e:
                                        if debug:
                                            print(f"   Could not save skipped page debug image: {e}")
                                table = []
                                labels = []
                            
                            page_tables[label] = table
                            page_headers[label] = labels
                            
                            if debug:
                                print(f"   ✅ Completed processing config [{config_num}/{len(page_configs)}] for label: {label}")
                        except Exception as e:
                            import traceback
                            if debug:
                                print(f"\n❌ Exception in config [{config_num}/{len(page_configs)}] (label: {label}):")
                                print(f"   Error: {str(e)}")
                                traceback.print_exc()
                            # Still add empty entries so the loop continues
                            page_tables[label] = []
                            page_headers[label] = []

                    if debug:
                        print(f"\n📊 Summary: Processed {len(page_tables)} table(s) for {name}")
                        print(f"   Labels processed: {list(page_tables.keys())}")
                    
                    rec = parse_record(name, page_tables, page_headers, pdf_size, config)
                    if debug:
                        print("rec", rec)
                        print(f"\n✅ Completed processing {len(page_configs)} configuration(s) for {name}")
                    records.append(rec)

            except Exception as e:
                import traceback
                if debug:
                    print(f"\n❌ Exception occurred while processing {name}:")
                    print(f"   Error: {str(e)}")
                    print(f"   Traceback:")
                    traceback.print_exc()
                err_obj = {"file": name, "error": str(e), "pdf_size": pdf_size if 'pdf_size' in locals() else 0}
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
