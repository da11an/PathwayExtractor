# Extraction Configuration Files

This directory contains JSON configuration files that define how to extract tables from PDF files.

## Configuration Structure

Each configuration file defines:
- **format_name**: Unique identifier for this format
- **description**: Human-readable description
- **pages**: Array of page configurations

### Page Configuration

Each page configuration includes:
- **page_index**: Zero-based page index in the PDF (0 = first page, 1 = second page, etc.)
- **label**: Unique label for this page's data (e.g., "page2_text")
- **parser_module**: Python module path containing the parser function
- **parser_function**: Name of the function to parse the extracted table
- **test_function**: Name of the function to validate table rows (optional, defaults to "test_row")
- **extraction**: Extraction settings:
  - **target_header**: First word to search for when finding the table start
  - **start_top**: Initial Y position to start searching (in points)
  - **max_shift**: Maximum pixels to shift up/down when searching
  - **delta**: Step size for shifting
  - **header_height**: Height of the header row in points
  - **use_explicit_vertical_lines**: Whether to use detected header positions for column boundaries
  - **minimum_column_width**: Minimum width for columns when using explicit vertical lines
  - **left_bound**: Left X boundary in points (optional, defaults to 0 - full page width)
  - **right_bound**: Right X boundary in points (optional, defaults to page width - full page width)
  
  **Note:** When `left_bound` and/or `right_bound` are specified, the table extraction will be limited to that horizontal region. This is useful when there are multiple tables side by side on the same page.

## Usage

### Using the default format (format_v1):
```bash
python main.py
```

### Using a custom configuration:
```bash
python main.py --config configs/format_v2.json
```

## Creating a New Configuration

### Option 1: Automatic Generation (Recommended)

Use the config generator to automatically analyze a sample PDF from a ZIP file and generate configuration:

```bash
python pathway_extractor/config_generator.py path/to/reports.zip
```

This will:
1. Extract PDFs from the ZIP file
2. Analyze the first PDF (or specify with `--pdf-index`)
3. Scan the PDF for table titles (centered text above tables)
4. Find the page index for each table
5. Estimate table bounds (left_bound, right_bound, start_top)
6. Detect the first column header (target_header)
7. Generate a complete configuration file

**Customizing the generator:**

Edit `configs/generator_config.json` to specify:
- Table titles to search for
- Expected first column headers
- Parser functions to use
- Default parameter hints

**Examples:**
```bash
# Generate config from ZIP (uses first PDF)
python pathway_extractor/config_generator.py reports.zip

# Use a specific PDF from the ZIP (by index)
python pathway_extractor/config_generator.py reports.zip --pdf-index 2

# Generate config with custom name
python pathway_extractor/config_generator.py reports.zip \
    --format-name format_v3 \
    --output configs/format_v3.json \
    --description "New PDF format from 2024"

# Also works with single PDF files
python pathway_extractor/config_generator.py sample.pdf
```

### Option 2: Manual Creation

1. Copy `format_v2.json` to a new file (e.g., `format_v3.json`)
2. Update the `format_name` and `description`
3. For each page you need to extract:
   - Set the correct `page_index` (zero-based)
   - Update the `label` to match your naming convention
   - Adjust extraction settings based on the PDF layout
   - Point to the appropriate parser functions

## Parser Functions

Parser functions should:
- Accept `(table: list, headers: list)` as arguments
- Return a dictionary that will be merged into the final record
- Handle empty tables and missing headers gracefully

Existing parsers are in `pathway_extractor.parsers.page_2`, `page_3`, and `page_4`.
