"""
Configuration generator for PDF extraction settings.

Analyzes a sample PDF from a ZIP file (or single PDF) to automatically generate 
extraction configuration by finding table titles and estimating extraction parameters.

Typical usage:
    python pathway_extractor/config_generator.py path/to/reports.zip
"""
import json
import io
import pdfplumber
from pathlib import Path
from zipfile import ZipFile
from typing import List, Dict, Any, Optional, Tuple
import argparse


def find_title_text(page, text: str) -> Optional[Dict[str, float]]:
    """
    Find title text on a page by matching the text content.
    Requires ALL words from the search text to be present in the title.
    The title's center position will be used to estimate table bounds.
    
    Args:
        page: pdfplumber page object
        text: Text to search for (full phrase - all words must be present)
    
    Returns:
        Dict with 'top', 'bottom', 'left', 'right', 'x_center', 'y_center', 'text' or None
    """
    words = page.extract_words()
    if not words:
        return None
    
    # Split target text into words for matching
    target_words = [w.lower().strip() for w in text.split() if w.strip()]
    if not target_words:
        return None
    
    # Group words by y-position (same line)
    y_groups = {}
    for word in words:
        y_key = round(word["top"], 1)
        if y_key not in y_groups:
            y_groups[y_key] = []
        y_groups[y_key].append(word)
    
    # Strategy 1: Look for lines that contain ALL target words
    # Search all lines first before accepting partial matches
    best_match = None
    best_match_score = 0
    
    for y_key, line_words in sorted(y_groups.items()):
        # Sort words by x position
        line_words_sorted = sorted(line_words, key=lambda w: w["x0"])
        line_text_lower = " ".join(w["text"].lower() for w in line_words_sorted)
        line_words_lower = [w["text"].lower() for w in line_words_sorted]
        
        # Check if ALL target words are present in this line
        all_words_present = all(
            any(target_word in line_word or line_word in target_word 
                for line_word in line_words_lower)
            for target_word in target_words
        )
        
        if all_words_present:
            # Calculate how well the match is (prefer exact phrase matches)
            # Score: number of target words found + bonus for exact phrase match
            score = len(target_words)
            
            # Check if the target phrase appears as a substring (exact match bonus)
            target_phrase = " ".join(target_words)
            if target_phrase in line_text_lower:
                score += 10  # Bonus for exact phrase match
            
            # Prefer matches with all words in order
            target_idx = 0
            for line_word in line_words_lower:
                if target_idx < len(target_words):
                    if target_words[target_idx] in line_word or line_word in target_words[target_idx]:
                        target_idx += 1
            if target_idx == len(target_words):
                score += 5  # Bonus for words in order
            
            if score > best_match_score:
                best_match_score = score
                phrase_left = line_words_sorted[0]["x0"]
                phrase_right = line_words_sorted[-1]["x1"]
                phrase_center_x = (phrase_left + phrase_right) / 2
                
                best_match = {
                    "top": min(w["top"] for w in line_words_sorted),
                    "bottom": max(w["bottom"] for w in line_words_sorted),
                    "left": phrase_left,
                    "right": phrase_right,
                    "x_center": phrase_center_x,
                    "y_center": (min(w["top"] for w in line_words_sorted) + max(w["bottom"] for w in line_words_sorted)) / 2,
                    "text": " ".join(w["text"] for w in line_words_sorted)
                }
    
    # Only return if we found a match with ALL words present
    if best_match and best_match_score >= len(target_words):
        return best_match
    
    return None


def find_table_below_title(page, title_y: float, title_x_center: float, 
                           page_width: float, gap: float = 30, 
                           max_search_distance: float = 200,
                           table_width_estimate: float = None,
                           title_left: float = None,
                           title_right: float = None) -> Optional[Dict[str, float]]:
    """
    Find the table that appears below a title.
    Uses the title's center and width to estimate table horizontal bounds.
    
    Args:
        page: pdfplumber page object
        title_y: Y position of the title (bottom)
        title_x_center: X center of the title (used to estimate table center)
        page_width: Width of the page
        gap: Expected gap between title and table
        max_search_distance: Maximum distance to search below title
        table_width_estimate: Estimated table width (if None, will estimate from content)
        title_left: Left edge of title (if provided, used as hint)
        title_right: Right edge of title (if provided, used as hint)
    
    Returns:
        Dict with table bounds (left, right, top, width) or None
    """
    # Start searching below the title
    search_start_y = title_y + gap
    search_end_y = title_y + gap + max_search_distance
    
    # Extract words below the title
    words = page.extract_words()
    table_words = [w for w in words if search_start_y <= w["top"] <= search_end_y]
    
    if not table_words:
        return None
    
    # Use title's x_center and width to estimate table horizontal bounds
    # Strategy: Use title width as hint, then detect column structures
    
    # Step 1: Use title width as initial estimate if available
    if title_left is not None and title_right is not None:
        title_width = title_right - title_left
        # Table is typically 1.5-3x wider than title
        initial_width_estimate = title_width * 2.2
    else:
        initial_width_estimate = None
    
    if table_width_estimate is None:
        # Step 2: Find words that form column-like structures
        # Group words by x-position to find vertical columns
        x_bins = {}
        bin_size = 25  # Group words within 25 points horizontally (slightly wider bins)
        for word in table_words:
            word_center_x = (word["x0"] + word["x1"]) / 2
            # Consider words reasonably close to title center (wider search area)
            if abs(word_center_x - title_x_center) < page_width * 0.5:
                bin_key = round(word_center_x / bin_size) * bin_size
                if bin_key not in x_bins:
                    x_bins[bin_key] = []
                x_bins[bin_key].append(word)
        
        if x_bins:
            # Find the densest column regions (columns have many words)
            # Sort bins by word count (most words = likely a column)
            sorted_bins = sorted(x_bins.items(), key=lambda x: len(x[1]), reverse=True)
            
            # Take the top bins that are near the title center
            relevant_bins = []
            for bin_x, bin_words in sorted_bins[:15]:  # Top 15 bins (more bins)
                if abs(bin_x - title_x_center) < page_width * 0.5:
                    relevant_bins.append((bin_x, bin_words))
            
            if relevant_bins:
                # Find significant columns (at least 2 words = header or data)
                # Lower threshold to catch more columns
                significant_bins = [(x, words) for x, words in relevant_bins if len(words) >= 2]
                
                if significant_bins:
                    # Get bounds from significant columns
                    all_words_in_columns = [w for _, words in significant_bins for w in words]
                    content_left = min(w["x0"] for w in all_words_in_columns)
                    content_right = max(w["x1"] for w in all_words_in_columns)
                    estimated_width = content_right - content_left
                    # Add moderate padding (10% on each side) to ensure we don't cut off edges
                    padding = estimated_width * 0.10
                    estimated_width = estimated_width + (padding * 2)
                else:
                    # Fallback: use all relevant bins
                    all_words = [w for _, words in relevant_bins for w in words]
                    if all_words:
                        content_left = min(w["x0"] for w in all_words)
                        content_right = max(w["x1"] for w in all_words)
                        estimated_width = content_right - content_left
                        # Add padding for fallback case too
                        padding = estimated_width * 0.10
                        estimated_width = estimated_width + (padding * 2)
                    else:
                        estimated_width = initial_width_estimate or page_width * 0.4
            else:
                # No good bins found, use initial estimate or default
                if initial_width_estimate:
                    estimated_width = initial_width_estimate
                else:
                    estimated_width = page_width * 0.4  # More moderate default
        else:
            # No words found, use initial estimate or default
            if initial_width_estimate:
                estimated_width = initial_width_estimate
            else:
                estimated_width = page_width * 0.4  # More moderate default
        
        # Constrain width to reasonable bounds (25-65% of page width - wider range)
        estimated_width = max(page_width * 0.25, min(estimated_width, page_width * 0.65))
    else:
        estimated_width = table_width_estimate
    
    # Center the table bounds around the title's center
    left_bound = max(0, title_x_center - estimated_width / 2)
    right_bound = min(page_width, title_x_center + estimated_width / 2)
    
    # Final refinement: Use name column (text) and numeric columns to set accurate bounds
    # Strategy: Find leftmost text column (names) and rightmost numeric column
    bounded_words = [w for w in table_words 
                     if left_bound <= (w["x0"] + w["x1"]) / 2 <= right_bound]
    
    if bounded_words:
        # Group words by x-position into columns
        column_groups = {}
        bin_size = 15
        for word in bounded_words:
            col_x = round((word["x0"] + word["x1"]) / 2 / bin_size) * bin_size
            if col_x not in column_groups:
                column_groups[col_x] = []
            column_groups[col_x].append(word)
        
        # Identify which columns contain text (names) vs numbers
        text_columns = []  # Columns with text (name column)
        numeric_columns = []  # Columns with numbers
        
        for col_x, words in column_groups.items():
            # Check if column has text (non-numeric) or numbers
            has_text = False
            has_numbers = False
            
            for word in words:
                word_text = word["text"].strip()
                # Check if word is numeric (allows for negative, decimal, etc.)
                # Remove common non-numeric chars and check
                cleaned = word_text.replace('-', '').replace('.', '').replace(',', '').strip()
                if cleaned and cleaned.replace(' ', '').isdigit():
                    has_numbers = True
                elif word_text and not word_text.replace('-', '').replace('.', '').isdigit():
                    # Has non-numeric characters (likely a name)
                    has_text = True
            
            if has_text and not has_numbers:
                # Pure text column (name column)
                text_columns.append(col_x)
            elif has_numbers:
                # Numeric column
                numeric_columns.append(col_x)
        
        # Find leftmost text column (name column) and rightmost numeric column
        if text_columns and numeric_columns:
            leftmost_text_col = min(text_columns)
            rightmost_numeric_col = max(numeric_columns)
            
            # Get bounds from these columns
            text_col_words = [w for w in bounded_words 
                            if round((w["x0"] + w["x1"]) / 2 / bin_size) * bin_size == leftmost_text_col]
            numeric_col_words = [w for w in bounded_words 
                               if round((w["x0"] + w["x1"]) / 2 / bin_size) * bin_size == rightmost_numeric_col]
            
            if text_col_words and numeric_col_words:
                # Set bounds based on name column left edge and numeric column right edge
                name_col_left = min(w["x0"] for w in text_col_words)
                numeric_col_right = max(w["x1"] for w in numeric_col_words)
                
                # Use these as the actual table bounds with padding
                # Add extra padding (5 points more) to ensure we don't cut off edges
                left_bound = max(0, name_col_left - 20)  # 15 + 5 = 20 points padding
                right_bound = min(page_width, numeric_col_right + 20)  # 15 + 5 = 20 points padding
                
                print(f"      Detected name column at x={leftmost_text_col:.1f}, numeric columns extend to x={rightmost_numeric_col:.1f}")
                print(f"      Applied padding: left={left_bound:.1f} (name_col={name_col_left:.1f}-20), right={right_bound:.1f} (numeric_col={numeric_col_right:.1f}+20)")
        elif text_columns:
            # Only found text columns, use leftmost text column
            leftmost_text_col = min(text_columns)
            text_col_words = [w for w in bounded_words 
                            if round((w["x0"] + w["x1"]) / 2 / bin_size) * bin_size == leftmost_text_col]
            if text_col_words:
                name_col_left = min(w["x0"] for w in text_col_words)
                left_bound = max(0, name_col_left - 20)  # 20 points padding
        elif numeric_columns:
            # Only found numeric columns, use rightmost numeric column
            rightmost_numeric_col = max(numeric_columns)
            numeric_col_words = [w for w in bounded_words 
                               if round((w["x0"] + w["x1"]) / 2 / bin_size) * bin_size == rightmost_numeric_col]
            if numeric_col_words:
                numeric_col_right = max(w["x1"] for w in numeric_col_words)
                right_bound = min(page_width, numeric_col_right + 20)  # 20 points padding
        else:
            # Fallback: use all columns
            all_cols = list(column_groups.keys())
            if all_cols:
                leftmost_col = min(all_cols)
                rightmost_col = max(all_cols)
                left_col_words = [w for w in bounded_words 
                                if round((w["x0"] + w["x1"]) / 2 / bin_size) * bin_size == leftmost_col]
                right_col_words = [w for w in bounded_words 
                                 if round((w["x0"] + w["x1"]) / 2 / bin_size) * bin_size == rightmost_col]
                if left_col_words and right_col_words:
                    left_bound = max(0, min(w["x0"] for w in left_col_words) - 25)  # 25 points padding for fallback
                    right_bound = min(page_width, max(w["x1"] for w in right_col_words) + 25)  # 25 points padding for fallback
    
    # Find the top of the table (header row, not first data row)
    # Look for the first row that looks like a header (typically has expected header words)
    if bounded_words:
        # Group words by y-position to find distinct rows
        y_groups = {}
        for word in bounded_words:
            y_key = round(word["top"], 1)
            if y_key not in y_groups:
                y_groups[y_key] = []
            y_groups[y_key].append(word)
        
        # Sort rows by y-position (top to bottom)
        sorted_rows = sorted(y_groups.items(), key=lambda x: x[0])
        
        # The header row is typically the first or second row
        # Use the first row as table_top (will be refined when finding header)
        table_top = sorted_rows[0][0] if sorted_rows else min(w["top"] for w in bounded_words)
    else:
        # Fallback: use search start if no words found in bounds
        table_top = search_start_y
    
    return {
        "left": left_bound,
        "right": right_bound,
        "top": table_top,
        "width": right_bound - left_bound
    }


def find_first_column_header(page, table_top: float, left_bound: float, 
                            right_bound: float, expected_headers: List[str],
                            title_y: float = None) -> Optional[str]:
    """
    Find the first column header by looking for expected header text.
    Searches near the title (header row is typically just below title).
    
    Args:
        page: pdfplumber page object
        table_top: Y position where table starts (may be data row, not header)
        left_bound: Left boundary of table
        right_bound: Right boundary of table
        expected_headers: List of possible header names to look for
        title_y: Y position of title (if provided, search near title instead of table_top)
    
    Returns:
        First matching header text or None
    """
    words = page.extract_words()
    
    # If title_y is provided, search near the title (header is typically 20-60 points below title)
    # Otherwise, search near table_top but look for header-like text
    if title_y is not None:
        search_y = title_y + 40  # Header typically ~40 points below title
        search_tolerance = 30
    else:
        search_y = table_top
        search_tolerance = 20  # Tighter tolerance when using table_top
    
    # Find words in the header row area
    header_words = []
    for word in words:
        # Check if word is in the header area
        if abs(word["top"] - search_y) <= search_tolerance:
            # Check if word is within table bounds and in the leftmost column area
            word_center_x = (word["x0"] + word["x1"]) / 2
            if left_bound <= word_center_x <= left_bound + (right_bound - left_bound) * 0.3:  # Left 30% of table
                header_words.append(word)
    
    if not header_words:
        # Fallback: search a bit wider area
        for word in words:
            if abs(word["top"] - search_y) <= search_tolerance * 2:
                word_center_x = (word["x0"] + word["x1"]) / 2
                if left_bound <= word_center_x <= right_bound:
                    header_words.append(word)
    
    if not header_words:
        return None
    
    # Sort by x position to get leftmost words first
    header_words.sort(key=lambda w: w["x0"])
    
    # Try to find a match with expected headers (prioritize exact matches)
    for word in header_words[:5]:  # Check first 5 words
        word_text_lower = word["text"].lower().strip()
        for expected in expected_headers:
            expected_lower = expected.lower().strip()
            # Exact match or contains match
            if expected_lower == word_text_lower or expected_lower in word_text_lower or word_text_lower in expected_lower:
                return word["text"]
    
    # If no match found, don't return a data value - return None so we can use the expected default
    return None


def analyze_pdf_for_tables(pdf_file, generator_config: Dict[str, Any], pdf_name: str = "PDF") -> List[Dict[str, Any]]:
    """
    Analyze a PDF to find tables and generate configuration.
    
    Args:
        pdf_file: PDF file path (str) or file-like object (BytesIO)
        generator_config: Generator configuration dict
        pdf_name: Name of the PDF for logging purposes
    
    Returns:
        List of page configurations found
    """
    table_titles_config = generator_config["table_titles"]
    defaults = generator_config.get("defaults", {})
    title_to_table_gap = defaults.get("title_to_table_gap", 30)
    table_width_padding = defaults.get("table_width_estimate_padding", 100)
    
    found_configs = []
    
    with pdfplumber.open(pdf_file) as pdf:
        print(f"📄 Analyzing {pdf_name} with {len(pdf.pages)} pages...")
        
        # Debug: Show page dimensions for first page
        if len(pdf.pages) > 0:
            print(f"   Page dimensions: {pdf.pages[0].width:.1f} x {pdf.pages[0].height:.1f} points")
        
        # Step 1: Find all titles across all pages, grouped by page
        # Structure: {page_idx: [(title_config_index, title_info, page, title_config), ...]}
        titles_by_page = {}
        for title_idx, title_config in enumerate(table_titles_config):
            title_text = title_config["title_text"]
            print(f"\n🔍 Looking for table title: '{title_text}'")
            
            # Search ALL pages for this title
            all_page_matches = []
            for page_idx, page in enumerate(pdf.pages):
                title_info = find_title_text(page, title_text)
                if title_info:
                    all_page_matches.append((page_idx, title_info, page))
            
            if all_page_matches:
                # Prefer exact phrase matches, then matches on earlier pages
                all_page_matches.sort(key=lambda x: (
                    -1 if title_text.lower() in x[1]["text"].lower() else 0,  # Exact phrase first
                    x[0]  # Then by page index
                ))
                page_idx, title_info, page = all_page_matches[0]
                
                if page_idx not in titles_by_page:
                    titles_by_page[page_idx] = []
                titles_by_page[page_idx].append((title_idx, title_info, page, title_config))
                
                print(f"   ✅ Found on page {page_idx} (zero-based)")
                print(f"      Detected text: '{title_info['text']}'")
                print(f"      Title position: y={title_info['y_center']:.1f}, x_center={title_info['x_center']:.1f}")
            else:
                print(f"   ❌ Title '{title_text}' not found in PDF")
        
        # Step 2: For pages with multiple titles, calculate midpoints between adjacent titles
        # Structure: {page_idx: {title_idx: (left_bound, right_bound)}}
        page_boundaries = {}
        for page_idx, titles in titles_by_page.items():
            if len(titles) > 1:
                # Sort titles by x_center (left to right)
                titles_sorted = sorted(titles, key=lambda x: x[1]["x_center"])
                page_width = titles_sorted[0][2].width  # Get page width from first title's page
                
                print(f"\n📐 Page {page_idx} has {len(titles_sorted)} tables - calculating boundaries:")
                boundaries = {}
                
                for i, (title_idx, title_info, page, title_config) in enumerate(titles_sorted):
                    if i == 0:
                        # Leftmost table: use page left edge and midpoint to next table
                        if len(titles_sorted) > 1:
                            midpoint = (title_info["x_center"] + titles_sorted[1][1]["x_center"]) / 2
                            left_bound = 0
                            right_bound = midpoint
                            print(f"   [{title_config['label']}] Left table: left={left_bound:.1f}, right={right_bound:.1f} (midpoint with next: {midpoint:.1f})")
                        else:
                            left_bound = 0
                            right_bound = page_width
                            print(f"   [{title_config['label']}] Single table: left={left_bound:.1f}, right={right_bound:.1f}")
                    elif i == len(titles_sorted) - 1:
                        # Rightmost table: use midpoint from previous table and page right edge
                        midpoint = (titles_sorted[i-1][1]["x_center"] + title_info["x_center"]) / 2
                        left_bound = midpoint
                        right_bound = page_width
                        print(f"   [{title_config['label']}] Right table: left={left_bound:.1f}, right={right_bound:.1f} (midpoint with previous: {midpoint:.1f})")
                    else:
                        # Middle table: use midpoints with both neighbors
                        left_midpoint = (titles_sorted[i-1][1]["x_center"] + title_info["x_center"]) / 2
                        right_midpoint = (title_info["x_center"] + titles_sorted[i+1][1]["x_center"]) / 2
                        left_bound = left_midpoint
                        right_bound = right_midpoint
                        print(f"   [{title_config['label']}] Middle table: left={left_bound:.1f}, right={right_bound:.1f}")
                    
                    boundaries[title_idx] = (left_bound, right_bound)
                
                page_boundaries[page_idx] = boundaries
        
        # Step 3: Process each title and create configs with appropriate boundaries
        for page_idx, titles in titles_by_page.items():
            for title_idx, title_info, page, title_config in titles:
                
                title_text = title_config["title_text"]
                print(f"\n📋 Processing: '{title_text}' on page {page_idx}")
                
                # Verify all required words are present
                title_words_found = [w.lower() for w in title_info['text'].split()]
                required_words = [w.lower() for w in title_text.split()]
                missing_words = [w for w in required_words 
                               if not any(w in found or found in w for found in title_words_found)]
                if missing_words:
                    print(f"      ⚠️  Warning: Some required words may be missing: {missing_words}")
                else:
                    print(f"      ✓ All required words present: {required_words}")
                
                # Determine table bounds
                # If this page has multiple tables, use calculated boundaries from midpoints
                if page_idx in page_boundaries and title_idx in page_boundaries[page_idx]:
                    left_bound, right_bound = page_boundaries[page_idx][title_idx]
                    print(f"      Using calculated boundaries from midpoints: left={left_bound:.1f}, right={right_bound:.1f}")
                    # Find table below title to get table_top, but use calculated boundaries
                    table_info = find_table_below_title(
                        page, 
                        title_info["bottom"],
                        title_info["x_center"],
                        page.width,
                        gap=title_to_table_gap,
                        table_width_estimate=right_bound - left_bound,  # Use calculated width
                        title_left=title_info["left"],
                        title_right=title_info["right"]
                    )
                    # Override with calculated boundaries
                    if table_info:
                        table_info["left"] = left_bound
                        table_info["right"] = right_bound
                        table_info["width"] = right_bound - left_bound
                else:
                    # Single table on page - use normal detection with title width hint
                    table_info = find_table_below_title(
                        page, 
                        title_info["bottom"],
                        title_info["x_center"],
                        page.width,
                        gap=title_to_table_gap,
                        table_width_estimate=None,
                        title_left=title_info["left"],
                        title_right=title_info["right"]
                    )
                
                if table_info:
                    print(f"      Table bounds: left={table_info['left']:.1f}, right={table_info['right']:.1f}, top={table_info['top']:.1f}")
                    print(f"      Table width: {table_info['width']:.1f} points")
                    print(f"      Table center: {(table_info['left'] + table_info['right']) / 2:.1f} (title center: {title_info['x_center']:.1f})")
                    
                    # Find first column header (search near title, not table_top which may be data)
                    expected_headers = title_config.get("expected_first_column_header", ["Name"])
                    target_header = find_first_column_header(
                        page,
                        table_info["top"],
                        table_info["left"],
                        table_info["right"],
                        expected_headers,
                        title_y=title_info["bottom"]  # Use title position to find header
                    )
                    
                    if target_header:
                        print(f"      First column header: '{target_header}'")
                    else:
                        print(f"      ⚠️  Could not find first column header, using first expected: '{expected_headers[0]}'")
                        target_header = expected_headers[0]
                    
                    # Get hints for other parameters
                    hints = title_config.get("hints", {})
                    
                    # Estimate start_top (position where table header row starts)
                    # Use hint if available, otherwise estimate from title position
                    if "typical_start_top" in hints:
                        estimated_start_top = hints["typical_start_top"]
                        print(f"      Using hint for start_top: {estimated_start_top}")
                    else:
                        # Estimate: header is typically 30-50 points below title
                        estimated_start_top = title_info["bottom"] + 40
                        print(f"      Estimated start_top from title: {estimated_start_top:.1f}")
                    
                    # Create page configuration
                    page_config = {
                        "page_index": page_idx,
                        "label": title_config["label"],
                        "parser_module": title_config["parser_module"],
                        "parser_function": title_config["parser_function"],
                        "test_function": title_config.get("test_function", "test_row"),
                        "extraction": {
                            "target_header": target_header,
                            "start_top": round(estimated_start_top),
                            "left_bound": round(table_info["left"]),
                            "right_bound": round(table_info["right"]),
                            "max_shift": hints.get("max_shift", 150),
                            "delta": hints.get("delta", 20),
                            "header_height": hints.get("typical_header_height", 25),
                            "use_explicit_vertical_lines": defaults.get("use_explicit_vertical_lines", True),
                            "minimum_column_width": hints.get("minimum_column_width", 17)
                        }
                    }
                    
                    found_configs.append(page_config)
                else:
                    print(f"      ⚠️  Found title but could not locate table below it")
    
    return found_configs


def generate_config_file(found_configs: List[Dict[str, Any]], output_path: str, 
                         format_name: str = "format_auto", description: str = "Auto-generated configuration"):
    """
    Generate a configuration JSON file from found configurations.
    
    Args:
        found_configs: List of page configurations
        output_path: Path to output JSON file
        format_name: Name for the format
        description: Description of the format
    """
    config = {
        "format_name": format_name,
        "description": description,
        "pages": found_configs
    }
    
    with open(output_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"\n✅ Configuration saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate PDF extraction configuration by analyzing a sample PDF from a ZIP file"
    )
    parser.add_argument(
        "input_path",
        type=str,
        help="Path to ZIP file containing PDFs (or single PDF file)"
    )
    parser.add_argument(
        "--pdf-index",
        type=int,
        default=0,
        help="Index of PDF to analyze from ZIP (default: 0, first PDF)"
    )
    parser.add_argument(
        "--generator-config",
        type=str,
        default=None,
        help="Path to generator config JSON (default: configs/generator_config.json)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output path for generated config (default: configs/format_auto.json)"
    )
    parser.add_argument(
        "--format-name",
        type=str,
        default="format_auto",
        help="Name for the generated format (default: format_auto)"
    )
    parser.add_argument(
        "--description",
        type=str,
        default="Auto-generated configuration from PDF analysis",
        help="Description for the generated format"
    )
    
    args = parser.parse_args()
    
    # Load generator config
    if args.generator_config is None:
        config_dir = Path(__file__).parent / "configs"
        generator_config_path = config_dir / "generator_config.json"
    else:
        generator_config_path = Path(args.generator_config)
    
    if not generator_config_path.exists():
        print(f"❌ Generator config not found: {generator_config_path}")
        print("   Please create a generator_config.json file first.")
        return
    
    with open(generator_config_path, 'r') as f:
        generator_config = json.load(f)
    
    input_path = Path(args.input_path)
    
    # Determine if input is ZIP or PDF
    if not input_path.exists():
        print(f"❌ Input file not found: {input_path}")
        return
    
    pdf_file = None
    pdf_name = "PDF"
    
    if input_path.suffix.lower() == '.zip':
        # Extract PDF from ZIP
        print(f"📦 Opening ZIP file: {input_path}")
        with ZipFile(input_path, 'r') as zf:
            pdf_names = [n for n in zf.namelist() if n.lower().endswith('.pdf')]
            
            if not pdf_names:
                print("❌ No PDF files found in ZIP")
                return
            
            print(f"   Found {len(pdf_names)} PDF file(s)")
            
            if args.pdf_index >= len(pdf_names):
                print(f"❌ PDF index {args.pdf_index} out of range (0-{len(pdf_names)-1})")
                print(f"   Available PDFs:")
                for i, name in enumerate(pdf_names):
                    print(f"      [{i}] {name}")
                return
            
            selected_pdf_name = pdf_names[args.pdf_index]
            pdf_name = selected_pdf_name
            print(f"   Analyzing PDF [{args.pdf_index}]: {selected_pdf_name}")
            
            # Read PDF data from ZIP
            with zf.open(selected_pdf_name) as pdf_data:
                pdf_file = io.BytesIO(pdf_data.read())
    else:
        # Single PDF file
        pdf_file = str(input_path)
        pdf_name = input_path.name
        print(f"📄 Analyzing PDF file: {input_path}")
    
    # Analyze PDF
    found_configs = analyze_pdf_for_tables(pdf_file, generator_config, pdf_name)
    
    if not found_configs:
        print("\n❌ No tables found. Please check:")
        print("   1. The PDF contains the expected table titles")
        print("   2. The generator_config.json has correct title texts")
        return
    
    # Generate output path
    if args.output is None:
        config_dir = Path(__file__).parent / "configs"
        output_path = config_dir / f"{args.format_name}.json"
    else:
        output_path = Path(args.output)
    
    # Generate config file
    generate_config_file(found_configs, str(output_path), args.format_name, args.description)
    
    print(f"\n📊 Generated configuration for {len(found_configs)} table(s)")
    print(f"   You can now use this config with: python pathway_extractor/main.py --config {output_path}")


if __name__ == "__main__":
    main()
