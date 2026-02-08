# Plan: Table Detection Improvements

## Goals
1. Detect if table titles are centered or left-aligned and adjust search strategy accordingly
2. Add detection of the last column header to better bound tables horizontally
3. Improve header row clipping to precisely extract only the header row (not title or data rows)

## Current State
- `find_table_bounds_by_expanding_from_title()` always expands from title center
- Only first column header is detected (`expected_first_column_header`)
- Header row uses fixed `header_height` which may include title or data rows

## Implementation Plan

### Step 1: Title Alignment Detection
**File**: `pathway_extractor/config_generator.py`

- Add function `detect_title_alignment(title_info, page_width)`:
  - Calculate title's x_center relative to page center
  - If title x_center is within 10% of page center → "centered"
  - If title left edge is within 5% of page left → "left_aligned"
  - Otherwise → "centered" (default)
  - Return alignment type

- Modify `find_table_bounds_by_expanding_from_title()`:
  - Call `detect_title_alignment()` to get alignment
  - For "centered": expand from title center (current behavior)
  - For "left_aligned": expand from title left edge (new behavior)
  - Adjust initial bounds and expansion logic based on alignment

### Step 2: Last Column Header Detection
**Files**: 
- `pathway_extractor/configs/generator_config.json`
- `pathway_extractor/config_generator.py`
- `pathway_extractor/config_loader.py`

- Add `expected_last_column_header` to generator_config.json (optional list, like first column)
- Update `find_table_bounds_by_expanding_from_title()`:
  - Accept `expected_last_headers` parameter
  - After finding first column header, search for last column header in the same row
  - Use last header's right edge to set final right bound
  - If last header not found, use current expansion logic as fallback
- Update `config_loader.py` to read `expected_last_column_header` from config
- Update `analyze_pdf_for_tables()` to pass last column headers to expansion function

### Step 3: Precise Header Row Clipping
**Files**: 
- `pathway_extractor/extractor.py`
- `pathway_extractor/config_generator.py`

- Add function `detect_header_row_bounds(page, first_header_word, last_header_word, title_y)`:
  - Find all words on the same line as first/last header words (within y_tolerance)
  - Determine header row's min_y (top) and max_y (bottom)
  - Return (header_top, header_bottom)
  
- Modify `find_table_bounds_by_expanding_from_title()`:
  - After finding first and last headers, call `detect_header_row_bounds()`
  - Return header_top and header_bottom in the bounds dict
  
- Modify `split_page_header_body()` in `extractor.py`:
  - Accept optional `header_top` and `header_bottom` parameters
  - If provided, use them instead of fixed `header_height`
  - Fall back to `header_height` if not provided (backward compatible)

- Update extraction flow in `extractor.py`:
  - Pass header_top/header_bottom from config to `split_page_header_body()`
  - Store header bounds in PageConfig if available

## Testing Strategy
1. Test with centered titles (existing PDFs)
2. Test with left-aligned titles (new PDFs)
3. Test with and without last column header specified
4. Verify header row clipping excludes title and data rows

## Files to Modify
1. `pathway_extractor/config_generator.py` - Add alignment detection, last header search, header bounds detection
2. `pathway_extractor/configs/generator_config.json` - Add `expected_last_column_header` examples
3. `pathway_extractor/config_loader.py` - Read last column header config
4. `pathway_extractor/extractor.py` - Use precise header bounds in clipping
