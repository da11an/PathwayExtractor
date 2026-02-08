import re
import io
import json
from zipfile import ZipFile
from pathlib import Path
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
        target: First word to search for, or list of possible headers to check
        start_top: Initial Y position to start searching
        max_shift: Maximum pixels to shift up/down
        delta: Step size for shifting
        left_bound: Left X boundary (None = 0, use full page)
        right_bound: Right X boundary (None = page.width, use full page)
    """
    # Normalize target to a list
    if isinstance(target, str):
        targets = [target]
    else:
        targets = target
    
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
        first_word = text.strip().split()[0] if text.strip() else ""
        
        # Check if first word matches any of the target headers
        for t in targets:
            if first_word == t or (t.lower() in first_word.lower() or first_word.lower() in t.lower()):
                # Return the cropped page and the top position
                # Note: top is the Y position in the original page coordinates
                return cropped, top

    return None, None  # target not found


def split_page_header_body(page, top_crop=0, header_height=25, left_bound=None, right_bound=None,
                          header_top=None, header_bottom=None, original_crop_y=0):
    """
    Crops a page into two: one for header row, one for the table body.
    Returns (header_page, body_page)
    
    Args:
        page: pdfplumber page object (already cropped horizontally and vertically)
        top_crop: Y position where table starts (relative to the cropped page, typically 0)
        header_height: Height of the header row (used if header_top/header_bottom not provided)
        left_bound: Left X boundary (None = 0, use full cropped page width)
        right_bound: Right X boundary (None = page.width, use full cropped page width)
        header_top: Precise top Y of header row in original page coordinates (optional)
        header_bottom: Precise bottom Y of header row in original page coordinates (optional)
        original_crop_y: Y position in original page where this cropped page starts (for coordinate conversion)
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
    
    # Determine header row bounds
    if header_top is not None and header_bottom is not None:
        # Use precise header bounds
        # Note: pdfplumber cropped pages maintain original page coordinate system in their bbox
        # So header_top/header_bottom (in original coords) can be used directly
        # But we need to ensure they're within the cropped page's bounds
        header_top_final = max(page_top, header_top)
        header_bottom_final = min(page_bottom, header_bottom)
        # Ensure header_bottom > header_top
        if header_bottom_final <= header_top_final:
            header_bottom_final = header_top_final + header_height
    else:
        # Use fixed header_height (fallback)
        header_top_final = page_top + top_crop
        header_bottom_final = header_top_final + header_height
    
    body_top = header_bottom_final
    body_bottom = page_bottom
    
    header_bbox = (left, header_top_final, right, header_bottom_final)
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


def find_title_on_page(page, title_text):
    """
    Find a title on a page by matching a sequence of words.

    Args:
        page: pdfplumber page object
        title_text: Full title string (e.g., "Assignments Submitted by Week")

    Returns:
        Dict with {"x0", "x1", "top", "bottom"} or None if not found
    """
    target_words = [w.lower() for w in title_text.split() if w.strip()]
    if not target_words:
        return None

    words = page.extract_words()
    if not words:
        return None

    # Group words by Y position (same line)
    y_groups = {}
    for w in words:
        y_key = round(w["top"], 0)
        if y_key not in y_groups:
            y_groups[y_key] = []
        y_groups[y_key].append(w)

    for y_key, line_words in sorted(y_groups.items()):
        line_words_sorted = sorted(line_words, key=lambda w: w["x0"])
        line_words_lower = [w["text"].lower().lstrip('*') for w in line_words_sorted]

        # Try to find contiguous sequence matching target_words
        for start_idx in range(len(line_words_sorted)):
            if start_idx + len(target_words) > len(line_words_sorted):
                break

            match = True
            for j, target_word in enumerate(target_words):
                candidate = line_words_lower[start_idx + j]
                if target_word not in candidate and candidate not in target_word:
                    match = False
                    break

            if match:
                matched = line_words_sorted[start_idx:start_idx + len(target_words)]
                return {
                    "x0": matched[0]["x0"],
                    "x1": matched[-1]["x1"],
                    "top": min(w["top"] for w in matched),
                    "bottom": max(w["bottom"] for w in matched),
                }

    return None


def find_header_row(page, title_bottom, expected_first_headers, y_search_range=60):
    """
    Find the header row below a title, returning labeled column positions.

    Args:
        page: pdfplumber page object
        title_bottom: Y position of the title's bottom edge
        expected_first_headers: List of possible first column header texts
        y_search_range: How far below title_bottom to search

    Returns:
        (header_positions, header_top, header_bottom) where header_positions is
        [(label, x0, x1), ...] sorted by x0, or ([], None, None) if not found
    """
    words = page.extract_words()
    if not words:
        return [], None, None

    # Normalize expected headers for comparison
    expected_lower = [h.lower() for h in expected_first_headers]

    # Search below title for a word matching any expected first header
    anchor_word = None
    for w in words:
        if w["top"] < title_bottom or w["top"] > title_bottom + y_search_range:
            continue
        w_text = w["text"].strip().lower()
        for exp in expected_lower:
            if w_text == exp or exp in w_text or w_text in exp:
                if anchor_word is None or w["top"] < anchor_word["top"]:
                    anchor_word = w
                break

    if anchor_word is None:
        return [], None, None

    anchor_y = anchor_word["top"]
    y_tolerance = 3

    # Collect ALL words on the same Y line
    header_words = [w for w in words if abs(w["top"] - anchor_y) <= y_tolerance]
    header_words.sort(key=lambda w: w["x0"])

    if not header_words:
        return [], None, None

    header_top = min(w["top"] for w in header_words)
    header_bottom = max(w["bottom"] for w in header_words)

    # Group adjacent words into multi-word headers (spacing threshold ~5pt)
    spacing_threshold = 5
    positions = []
    current_label = ""
    current_x0 = None
    current_x1 = None

    for i, w in enumerate(header_words):
        text = w["text"].strip()
        if not current_label:
            current_label = text
            current_x0 = w["x0"]
            current_x1 = w["x1"]
        else:
            gap = w["x0"] - current_x1
            if gap <= spacing_threshold:
                current_label += " " + text
                current_x1 = w["x1"]
            else:
                positions.append((current_label, current_x0, current_x1))
                current_label = text
                current_x0 = w["x0"]
                current_x1 = w["x1"]

    if current_label:
        positions.append((current_label, current_x0, current_x1))

    return positions, header_top, header_bottom


def compute_column_boundaries(header_positions, left_bound=None, right_bound=None):
    """
    Compute column boundaries from header positions using midpoints between adjacent headers.

    Args:
        header_positions: [(label, x0, x1), ...] sorted by x0
        left_bound: Left edge of table (or None to use first header x0 - 10)
        right_bound: Right edge of table (or None to use last header x1 + 10)

    Returns:
        [(col_start, col_end), ...] parallel to header_positions
    """
    if not header_positions:
        return []

    first_start = left_bound if left_bound is not None else header_positions[0][1] - 10
    last_end = right_bound if right_bound is not None else header_positions[-1][2] + 10

    boundaries = []
    for i in range(len(header_positions)):
        if i == 0:
            col_start = first_start
        else:
            # Midpoint between previous header's x1 and this header's x0
            col_start = (header_positions[i - 1][2] + header_positions[i][1]) / 2

        if i == len(header_positions) - 1:
            col_end = last_end
        else:
            col_end = (header_positions[i][2] + header_positions[i + 1][1]) / 2

        boundaries.append((col_start, col_end))

    return boundaries


def find_table_bottom(page, first_col_bounds, header_bottom_y):
    """
    Find the bottom of the table by looking for the last row with text in the first column.

    Args:
        page: pdfplumber page object
        first_col_bounds: (col_start, col_end) for the first column
        header_bottom_y: Y position of the header row bottom

    Returns:
        Bottom Y position of the last data row
    """
    words = page.extract_words()
    col_start, col_end = first_col_bounds

    # Find all words in the first column below the header
    first_col_words = []
    for w in words:
        word_center_x = (w["x0"] + w["x1"]) / 2
        if col_start <= word_center_x <= col_end and w["top"] > header_bottom_y:
            first_col_words.append(w)

    if not first_col_words:
        return header_bottom_y + 50  # Fallback

    # Group into rows by Y position
    y_tolerance = 5
    first_col_words.sort(key=lambda w: w["top"])
    rows = []
    current_row = [first_col_words[0]]

    for w in first_col_words[1:]:
        if abs(w["top"] - current_row[0]["top"]) <= y_tolerance:
            current_row.append(w)
        else:
            rows.append(current_row)
            current_row = [w]
    rows.append(current_row)

    # Return the bottom of the last row
    last_row = rows[-1]
    return max(w["bottom"] for w in last_row)


def extract_table_by_words(page, col_boundaries, header_labels, top_y, bottom_y):
    """
    Extract table data by assigning words to columns based on x-position.

    Args:
        page: pdfplumber page object
        col_boundaries: [(col_start, col_end), ...] for each column
        header_labels: [str, ...] column headers (parallel to col_boundaries)
        top_y: Top Y of data area (below header)
        bottom_y: Bottom Y of data area

    Returns:
        list[list[str]] where each row has one string per column
    """
    words = page.extract_words()

    # Filter words to the data area
    data_words = [w for w in words if w["top"] >= top_y and w["top"] <= bottom_y]

    if not data_words:
        return []

    # Group words into rows by Y position
    y_tolerance = 5
    data_words.sort(key=lambda w: w["top"])

    row_groups = []
    current_group = [data_words[0]]

    for w in data_words[1:]:
        if abs(w["top"] - current_group[0]["top"]) <= y_tolerance:
            current_group.append(w)
        else:
            row_groups.append(current_group)
            current_group = [w]
    row_groups.append(current_group)

    # For each row, assign words to columns
    table = []
    for row_words in row_groups:
        row = [""] * len(col_boundaries)
        # Sort words by x0 for proper left-to-right concatenation
        row_words.sort(key=lambda w: w["x0"])

        for w in row_words:
            word_center = (w["x0"] + w["x1"]) / 2
            # Find which column this word belongs to
            for col_idx, (col_start, col_end) in enumerate(col_boundaries):
                if col_start <= word_center <= col_end:
                    if row[col_idx]:
                        row[col_idx] += " " + w["text"]
                    else:
                        row[col_idx] = w["text"]
                    break

        table.append(row)

    return table


def extract_table_v2(page, title_text, expected_first_headers, expected_last_headers=None,
                     left_bound=None, right_bound=None, debug=False):
    """
    Extract a table from a page using word-position-based extraction.

    Orchestrates: find_title → find_header_row → compute_boundaries → find_bottom → extract_by_words

    Args:
        page: pdfplumber page object
        title_text: Title text to find (e.g., "Assignments Submitted by Week")
        expected_first_headers: List of possible first column header texts
        expected_last_headers: Optional list of possible last column header texts
            (used to truncate headers when side-by-side tables share a header row)
        left_bound: Optional left boundary for column computation
        right_bound: Optional right boundary for column computation
        debug: Enable debug logging

    Returns:
        (table, headers) where table is list[list[str]] and headers is list[str]
    """
    # Step 1: Find the title
    title_info = find_title_on_page(page, title_text)
    if title_info is None:
        if debug:
            print(f"   [v2] Title '{title_text}' not found on page")
        return [], []

    if debug:
        print(f"   [v2] Found title '{title_text}' at y={title_info['top']:.1f}-{title_info['bottom']:.1f}")

    # Step 2: Find the header row
    header_positions, header_top, header_bottom = find_header_row(
        page, title_info["bottom"], expected_first_headers
    )

    if not header_positions:
        if debug:
            print(f"   [v2] Header row not found below title")
        return [], []

    # Truncate at expected last header to avoid picking up adjacent table headers
    if expected_last_headers:
        last_lower = [h.lower() for h in expected_last_headers]
        truncate_idx = None
        for i, (label, x0, x1) in enumerate(header_positions):
            if label.lower() in last_lower:
                truncate_idx = i
                # Don't break — use the FIRST match (leftmost) since a second "Total"
                # would belong to a different table
                break
        if truncate_idx is not None and truncate_idx < len(header_positions) - 1:
            if debug:
                removed = [pos[0] for pos in header_positions[truncate_idx + 1:]]
                print(f"   [v2] Truncating headers after '{header_positions[truncate_idx][0]}', removing: {removed}")
            header_positions = header_positions[:truncate_idx + 1]

    header_labels = [pos[0] for pos in header_positions]
    if debug:
        print(f"   [v2] Found {len(header_positions)} headers: {header_labels}")
        for label, x0, x1 in header_positions:
            print(f"         '{label}': x0={x0:.1f}, x1={x1:.1f}")

    # Step 3: Compute column boundaries
    col_boundaries = compute_column_boundaries(header_positions, left_bound, right_bound)

    if debug:
        for i, ((label, _, _), (cs, ce)) in enumerate(zip(header_positions, col_boundaries)):
            print(f"         Col {i} '{label}': [{cs:.1f}, {ce:.1f}]")

    # Step 4: Find table bottom
    table_bottom = find_table_bottom(page, col_boundaries[0], header_bottom)

    if debug:
        print(f"   [v2] Table body: y={header_bottom:.1f} to {table_bottom:.1f}")

    # Step 5: Extract table data
    table = extract_table_by_words(page, col_boundaries, header_labels, header_bottom, table_bottom)

    if debug:
        print(f"   [v2] Extracted {len(table)} data rows")
        if table:
            print(f"         First row: {table[0]}")

    return table, header_labels


def extract_largest_table(page, table_settings=None, label=None, debug=False, debug_dir=None):
    """
    Extract the largest table from a page, prioritizing by row count then column count.
    
    Args:
        page: pdfplumber page object
        table_settings: Settings for table extraction
        label: Label for debug image filename (optional)
        debug: Whether to save debug images
        debug_dir: Directory to save debug images (Path object or None)
        
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
    if debug and label is not None and debug_dir is not None:
        debug_tablefinder_filename = debug_dir / f"debug_tablefinder_{label}.png"
        page.to_image(resolution=200).debug_tablefinder(table_settings=table_settings).save(str(debug_tablefinder_filename))
        print(f"   💾 Saved table finder debug image: {debug_tablefinder_filename}")
    
    if not tables:
        return []
    
    # Find the largest table by row count, then by column count
    largest_table = max(tables, key=lambda table: (
        len(table) if table else 0,  # Row count
        max(len(row) for row in table) if table and table[0] else 0  # Max column count
    ))
    
    return largest_table or []


def parse_record(file_name: str, page_tables: dict, page_headers: dict, pdf_size: float, config: ExtractionConfig, debug: bool = False) -> dict:
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
        
        if debug:
            print(f"🔍 Parsing {label}: {len(table_data)} rows, {len(headers)} headers")
            if table_data:
                print(f"   First row: {table_data[0]}")
            if headers:
                print(f"   Headers: {headers}")
        
        # Pass the target_header to the parser function
        result = parser_func(table_data, headers, target_header=page_config.target_header)
        
        if debug:
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
    config: Optional[ExtractionConfig] = None,
    debug_dir: Optional[Path] = None,
    generator_config: dict = None
) -> list:
    """
    Process all PDFs in a zip file and return list of extracted records.

    Args:
        zip_path: Path to zip file containing PDFs
        max_files: Maximum number of files to process (None for all)
        filename_filter: Filter PDFs by filename substring (None for all)
        debug: Enable debug output
        config: ExtractionConfig object. If None, loads default config.
        debug_dir: Directory to save debug artifacts (Path object or None)
        generator_config: Generator config dict. When provided, uses v2 word-position extraction.

    Returns:
        List of extracted records
    """
    # V2 path: word-position-based extraction using generator_config
    if generator_config is not None:
        return _extract_records_v2(zip_path, max_files, filename_filter, debug, debug_dir, generator_config)

    # V1 path: original pdfplumber table extraction
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

                                if debug:
                                    # Print page dimensions - useful for configuration debugging
                                    print(f"   Page {idx} dimensions: {original_page.width:.1f} x {original_page.height:.1f} points")
                                    print(f"   Searching for target header: '{page_config.target_header}'")

                                # Save original full page for reference (only once per page index, but include label for uniqueness)
                                if debug and debug_dir is not None:
                                    debug_original_filename = debug_dir / f"debug_original_{label}.png"
                                    original_page.to_image(resolution=150).save(str(debug_original_filename))
                                    print(f"   💾 Saved original full page: {debug_original_filename}")

                                # Save horizontally cropped page if bounds are set
                                if debug and debug_dir is not None and (page_config.left_bound is not None or page_config.right_bound is not None):
                                    left = page_config.left_bound if page_config.left_bound is not None else 0
                                    right = page_config.right_bound if page_config.right_bound is not None else original_page.width
                                    horizontally_cropped = original_page.within_bbox((left, 0, right, original_page.height))
                                    debug_horizontal_filename = debug_dir / f"debug_horizontal_crop_{label}_left{int(left)}_right{int(right)}.png"
                                    horizontally_cropped.to_image(resolution=150).save(str(debug_horizontal_filename))
                                    print(f"   💾 Saved horizontally cropped page: {debug_horizontal_filename}")

                                # Use config values for crop finding with horizontal bounds
                                # Use all expected headers, not just target_header
                                target_headers = getattr(page_config, 'expected_headers', [page_config.target_header])
                                page, top_crop_original = find_correct_crop(
                                    original_page,
                                    target=target_headers,  # Pass list of all expected headers
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
                                        if debug_dir is not None:
                                            left = page_config.left_bound if page_config.left_bound is not None else 0
                                            right = page_config.right_bound if page_config.right_bound is not None else original_page.width
                                            failed_crop = original_page.within_bbox((left, page_config.start_top, right, original_page.height))
                                            debug_failed_filename = debug_dir / f"debug_failed_crop_{label}_start{int(page_config.start_top)}.png"
                                            failed_crop.to_image(resolution=150).save(str(debug_failed_filename))
                                            print(f"   💾 Saved failed crop attempt: {debug_failed_filename}")
                                    table = []
                                    labels = []
                                else:
                                    # Save the cropped page at top_crop_original for inspection
                                    if debug and debug_dir is not None:
                                        # Recreate the exact crop that was found for inspection
                                        left = page_config.left_bound if page_config.left_bound is not None else 0
                                        right = page_config.right_bound if page_config.right_bound is not None else original_page.width
                                        cropped_for_inspection = original_page.within_bbox((left, top_crop_original, right, original_page.height))
                                        debug_cropped_filename = debug_dir / f"debug_cropped_{label}_top{int(top_crop_original)}.png"
                                        cropped_for_inspection.to_image(resolution=150).save(str(debug_cropped_filename))
                                        print(f"   💾 Saved cropped page at top={top_crop_original:.1f}: {debug_cropped_filename}")

                                    # The page returned by find_correct_crop is cropped starting from top_crop_original
                                    # So within the cropped page, the header is at Y=0 (or close to it)
                                    # We need to adjust top_crop to be relative to the cropped page
                                    # Since the page is cropped from top_crop_original, the header should be at Y=0
                                    top_crop_in_cropped_page = 0

                                    # Note: page is already cropped horizontally and vertically by find_correct_crop
                                    # So we pass None for bounds and use top_crop_in_cropped_page
                                    # If precise header bounds are available, use them (convert from original page coords)
                                    header_page, body_page = split_page_header_body(
                                        page,
                                        top_crop=top_crop_in_cropped_page,
                                        header_height=page_config.header_height,
                                        left_bound=None,  # Page already cropped horizontally
                                        right_bound=None,  # Page already cropped horizontally
                                        header_top=getattr(page_config, 'header_top', None),
                                        header_bottom=getattr(page_config, 'header_bottom', None),
                                        original_crop_y=top_crop_original  # Pass original crop Y for coordinate conversion
                                    )

                                    # Debugging - save all crop stages
                                    if debug and debug_dir is not None:
                                        debug_raw_filename = debug_dir / f"debug_raw_{label}.png"
                                        debug_header_filename = debug_dir / f"debug_header_{label}.png"
                                        debug_body_filename = debug_dir / f"debug_body_{label}.png"
                                        page.to_image(resolution=150).save(str(debug_raw_filename))
                                        header_page.to_image(resolution=150).save(str(debug_header_filename))
                                        body_page.to_image(resolution=150).save(str(debug_body_filename))
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
                                            table = extract_largest_table(body_page, table_settings=table_settings, label=label, debug=debug, debug_dir=debug_dir)
                                        else:
                                            # No headers found, fall back to text-based extraction
                                            table = extract_largest_table(body_page, table_settings=None, label=label, debug=debug, debug_dir=debug_dir)
                                    else:
                                        table = extract_largest_table(body_page, table_settings=None, label=label, debug=debug, debug_dir=debug_dir)

                                    if debug:
                                        print("name", name)
                                        print("label", label)
                            else:
                                if debug:
                                    print(f"   ⚠️  Skipping: Page index {idx} is out of range (PDF has {len(pdf.pages)} pages, indices 0-{len(pdf.pages)-1})")
                                    # Still save a placeholder debug image to show this config was processed
                                    if debug_dir is not None:
                                        try:
                                            # Try to get the last available page as a reference
                                            if len(pdf.pages) > 0:
                                                ref_page = pdf.pages[-1]
                                                debug_skipped_filename = debug_dir / f"debug_skipped_{label}_page{idx}_not_found.png"
                                                ref_page.to_image(resolution=150).save(str(debug_skipped_filename))
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

                    rec = parse_record(name, page_tables, page_headers, pdf_size, config, debug=debug)
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


def _extract_records_v2(
    zip_path: str,
    max_files: int,
    filename_filter: str,
    debug: bool,
    debug_dir: Optional[Path],
    generator_config: dict
) -> list:
    """
    V2 extraction path using word-position-based table extraction.

    Uses generator_config entries (with page_index already populated) to find
    tables by title text, extract headers from word positions, and assign data
    words to columns by x-coordinate.
    """
    import importlib

    table_titles = generator_config["table_titles"]

    records = []
    with ZipFile(zip_path, "r") as zf:
        pdf_names = [
            n for n in zf.namelist()
            if n.lower().endswith(".pdf") and (filename_filter is None or filename_filter in n)
        ]

        if max_files is not None:
            pdf_names = pdf_names[:max_files]

        for name in tqdm(pdf_names, desc="Processing PDFs (v2)"):
            try:
                pdf_size = zf.getinfo(name).file_size
                if debug:
                    print(f"\n{'='*60}")
                    print(f"[v2] Processing: {name} ({pdf_size} bytes)")

                with zf.open(name) as f:
                    data = f.read()
                with pdfplumber.open(io.BytesIO(data)) as pdf:
                    page_tables = {}
                    page_headers = {}

                    for config_num, title_entry in enumerate(table_titles, 1):
                        label = title_entry["label"]
                        title_text = title_entry["title_text"]
                        expected_first = title_entry.get("expected_first_column_header", ["Name"])
                        expected_last = title_entry.get("expected_last_column_header", None)
                        page_index = title_entry.get("page_index")

                        if debug:
                            print(f"\n   [{config_num}/{len(table_titles)}] '{title_text}' (label: {label}, page: {page_index})")

                        if page_index is None or page_index >= len(pdf.pages):
                            if debug:
                                print(f"   Skipping: page_index={page_index} out of range (PDF has {len(pdf.pages)} pages)")
                            page_tables[label] = []
                            page_headers[label] = []
                            continue

                        original_page = pdf.pages[page_index]

                        table, headers = extract_table_v2(
                            original_page,
                            title_text,
                            expected_first,
                            expected_last_headers=expected_last,
                            debug=debug
                        )

                        page_tables[label] = table
                        page_headers[label] = headers

                        if debug:
                            print(f"   Result: {len(table)} rows, {len(headers)} headers")

                    # Build record using parsers from generator_config
                    try:
                        filename_info = parse_filename(name)
                    except ValueError as e:
                        if debug:
                            print(f"   Warning: filename parsing failed: {e}")
                        filename_info = {"class_info": {}}

                    parsed = {
                        "file": name,
                        **filename_info,
                        "pdf_size": pdf_size,
                    }

                    for title_entry in table_titles:
                        label = title_entry["label"]
                        parser_module_name = title_entry["parser_module"]
                        parser_function_name = title_entry["parser_function"]
                        target_header = title_entry.get("expected_first_column_header", ["Name"])[0]

                        table_data = page_tables.get(label, [])
                        headers = page_headers.get(label, [])

                        # Load and call the parser
                        mod = importlib.import_module(parser_module_name)
                        parser_func = getattr(mod, parser_function_name)

                        if debug:
                            print(f"\n   Parsing {label}: {len(table_data)} rows, {len(headers)} headers")
                            if headers:
                                print(f"   Headers: {headers}")

                        result = parser_func(table_data, headers, target_header=target_header)
                        parsed.update(result)

                    if debug:
                        print(f"\n   Record keys: {list(parsed.keys())}")
                    records.append(parsed)

            except Exception as e:
                import traceback
                if debug:
                    print(f"\n   Exception processing {name}: {e}")
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
