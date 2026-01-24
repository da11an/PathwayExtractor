# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PathwayExtractor processes EnglishConnect 3 (EC3) progress report PDFs from ZIP bundles and generates per-student progress summary PNG images suitable for sharing via WhatsApp/SMS. The pipeline is fully in-memory with no intermediate file output.

## Common Commands

```bash
# Setup (one-time)
python3 -m venv venv_pathwayextractor
source venv_pathwayextractor/bin/activate  # Linux/macOS
pip install -e .
pip install -r requirements.txt
python post_install.py  # Install Playwright browsers

# Run the main pipeline
python pathway_extractor/main.py

# Run with custom extraction config
python pathway_extractor/main.py --config pathway_extractor/configs/format_v2.json

# Run with debug output (saves intermediate images)
python pathway_extractor/main.py --debug

# Auto-generate config from a ZIP file
python pathway_extractor/config_generator.py path/to/reports.zip
```

## Architecture

### Data Flow
1. **Input**: ZIP file of EC3 PDF reports (auto-selected from Downloads or via file dialog)
2. **Extraction** (`extractor.py`): Opens PDFs with pdfplumber, locates tables by searching for target headers
3. **Parsing** (`parsers/`): Each page type has a dedicated parser that transforms raw table data into structured records
4. **Transformation** (`parsers/utils.py:invert_student_data`): Converts class-level records into per-student records
5. **Rendering** (`generate_messages.py`): Generates HTML progress reports, converts to PNG via Playwright
6. **Output**: PNGs saved to `~/OneDrive/EC3 Learner Images/[zip_name]/[region_type]/[facilitator_day_time]/`

### Key Modules

- **`extractor.py`**: Core PDF extraction logic. `find_correct_crop()` locates table start by searching for target headers with configurable Y-offset. `extract_largest_table()` extracts the dominant table from a page region.

- **`config_loader.py`**: Loads JSON configs that define extraction parameters per page (page index, target header, crop bounds, parser function). `ExtractionConfig` and `PageConfig` classes lazy-load parser modules.

- **`parsers/`**: Page-specific parsers (`page_2.py`, `page_3.py`, `page_4.py`). Each parser accepts `(table, headers, target_header)` and returns a dict to merge into the record. `filename.py` parses class metadata from PDF filenames.

- **`generate_messages.py`**: Creates per-student PNG progress reports and a per-class `encouragement_messages.html` document for instructors.

- **`message_generator.py`**: Generates personalized encouraging messages based on student progress patterns.

### Configuration System

Extraction configs in `pathway_extractor/configs/` define how to extract tables from PDFs:
- `format_v1.json`, `format_v2.json`: Manual configs for known PDF formats
- `generator_config.json`: Defines table titles and expected headers for auto-generation
- `format_auto_generated.json`: Output from `config_generator.py`

Key extraction settings per page:
- `page_index`: Zero-based PDF page number
- `target_header`: First column header text to search for
- `start_top`, `max_shift`, `delta`: Y-position search parameters
- `left_bound`, `right_bound`: Horizontal crop boundaries (for side-by-side tables)
- `parser_module`, `parser_function`: Python module path to parsing function

## Debug Mode

Running with `--debug` saves intermediate images to `debug_output/[zip_name]/`:
- `debug_original_*.png`: Full page before cropping
- `debug_cropped_*.png`: Page after finding target header
- `debug_header_*.png`, `debug_body_*.png`: Split header and table body
- `debug_tablefinder_*.png`: pdfplumber's table detection visualization

## Data Conventions

- Unassessed skill levels are represented as `-1` internally, displayed as `-` in output
- Student names are sanitized for filesystem compatibility
- Weekly unit values are integers; invalid values default to 0
