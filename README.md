# EnglishConnect EC3 Progress Report Generator

This project extracts, parses, and visualizes student progress data from EnglishConnect 3 PDF reports. It converts ZIP bundles of class reports into per-student progress summary images that are suitable for sharing directly via messaging platforms like WhatsApp or SMS.

---

## Project Structure

```
pathway_extractor/
├── extractor.py # Extracts PDF data and parses filenames
├── generate_messages.py # Generates per-student HTML/PNG reports
├── parsers/
│ ├── filename_parser.py # Robust parsing of filename metadata
│ ├── pdf_parser.py # Handles PDF table extraction
│ └── utils.py # Data utilities (e.g., invert structure)
├── templates/
│ └── progress_report.html # Styled HTML template for student summaries
├── output/ # Output folder for generated student PNGs
main.py # Entry point to run everything
```

---

## How It Works

1. **Input**: A `.zip` file of EnglishConnect 3 PDF reports (e.g., downloaded from OneDrive)
2. **Extraction**: The ZIP is processed, and all relevant PDFs are parsed to extract tables and filenames
3. **Parsing**: Metadata is inferred from each filename (e.g., region, class type, day/time, facilitators)
4. **Transformation**: Class-level records are inverted into per-student records
5. **Rendering**: A personalized progress report is rendered to PNG for each student using HTML templates
6. **Output**: Each report is saved under the `output/` directory with class-based subfolders

---

## Design Principles

### No Database or JSONL Output
- While `.jsonl` files are used during development/testing, the runtime pipeline no longer outputs any structured intermediate files.
- The system processes data fully in-memory and produces final PNGs only.

### Robust Filename Parsing
- Designed to handle diverse naming conventions across regions
- Supports both virtual and in-person classes
- Gracefully skips or logs unrecognized formats

### Visual Reports
- HTML + CSS templates render clear tables and summaries
- PNGs are styled for visual appeal and quick comprehension
- Reports indicate unassessed skills (e.g., `-1`) as `-`

### Share-Ready Output
- Output PNGs are optimized for messaging platforms
- No need to open attachments—images can be viewed inline in WhatsApp or text threads

---

## Setup and Installation

### 1. Create and Activate Virtual Environment

**On Linux/macOS:**
```bash
python3 -m venv venv_pathwayextractor
source venv_pathwayextractor/bin/activate
```

**On Windows:**
```bash
python -m venv venv_pathwayextractor
venv_pathwayextractor\Scripts\activate
```

### 2. Install Dependencies

**Important:** You must install the package in editable mode so Python can find the `pathway_extractor` module:

```bash
pip install -e .
pip install -r requirements.txt
```

- `pip install -e .` installs the package itself in editable mode (required for imports to work)
- `pip install -r requirements.txt` installs all additional dependencies (Pillow, playwright, matplotlib, etc.)

### 3. Install Playwright Browsers

After installing dependencies, run the post-install script to set up Playwright browsers:

```bash
python post_install.py
```

This installs the browser binaries needed for HTML-to-PNG conversion.

---

## How to Run

### Option 1: From VS Code
1. Ensure your virtual environment is activated (see Setup above)
2. Open `pathway_extractor/main.py` in VS Code
3. Click the play button (▶️) to run the script

### Option 2: From Command Line

**On Linux/macOS:**
```bash
source venv_pathwayextractor/bin/activate
python pathway_extractor/main.py
```

**On Windows:**
```bash
venv_pathwayextractor\Scripts\activate
python pathway_extractor\main.py
```

### Running the Script

By default, `main.py` will attempt to load a ZIP file from your Downloads directory. If no ZIP is found, a file dialog will open to let you choose one.

**Note:** Make sure your virtual environment is activated before running the script. The script requires all dependencies to be installed and Playwright browsers to be set up (via `post_install.py`).

```
output/
└── [Region]_[Virtual or In person]/
    └── [Day_Time]_[First facilitator name]/
        └── Student Name.png
```

Each PNG contains:

- A personalized message from the facilitator
- Assessed level and units completed by skill
- Weekly unit completion
- Average units per week

# Running the full process

1. Access PDFs from Pathway Sharepoint: https://churchofjesuschrist.sharepoint.com/sites/BYUPW-MissionaryServices
2. Menu: EnglishConnect > Learner Progress Report > Learner Progress Report
3. Scroll to the bottom, then select all, download as zip
4. Run program
5. Write results to OneDrive: https://1drv.ms/f/c/947f531afae4cdba/EoN7uOBe7wRFi-foQjGAbYIByzNZLm2eFM2IpJ47KEHqVg

## Testing wrapped-name repair without generating images

Wrapped-name repair is **off by default**. Enable it with
`--repair-wrapped-names` when using the default auto-configuration (v2) path.
The existing title, header, crop, and column detection stays unchanged. The
additional repair requires an exact full-name text span on another extracted
PDF page, such as the no-submissions roster. Numeric cells separate text spans
when two tables share a printed line. It does not guess from name length or
join across numeric cells, and it leaves ambiguous cases unchanged.

Run one class through extraction and aggregation, without plots, PNG rendering,
or replacing an existing report directory:

```bash
venv_pathwayextractor/bin/python pathway_extractor/main.py \
  --zip ~/Downloads/OneDrive_2_2-19-2026.zip \
  --filename-filter Jahnke \
  --repair-wrapped-names \
  --extract-only debug_output/name_benchmark/one-class.json
```

Omit `--repair-wrapped-names` to compare the original behavior. `--zip` skips the
file chooser; `--filename-filter` matches instructor text or another filename
substring. `--extract-only` writes both the page records and aggregated student
records. The auto-generated extraction config is still written as usual.

For detailed comparisons, capture both modes against the same ZIP:

```bash
venv_pathwayextractor/bin/python scripts/benchmark_names.py \
  --zip ~/Downloads/OneDrive_2_2-19-2026.zip \
  --output debug_output/name_benchmark/latest
venv_pathwayextractor/bin/python scripts/benchmark_names.py \
  --zip ~/Downloads/OneDrive_2_2-19-2026.zip \
  --output debug_output/name_benchmark/latest --repair-wrapped-names
venv_pathwayextractor/bin/python scripts/compare_name_benchmarks.py \
  debug_output/name_benchmark/latest --require-complete
```

Use a fresh output directory for each ZIP. For smaller stages, the benchmark
runner accepts `--filter`, `--limit`, and `--files-from` (a JSON array of exact PDF
filenames). It saves raw tables, word coordinates, page text, parsed records,
aggregated records, logs, and per-PDF timings. Timings include diagnostic capture
and exclude rendering. These files contain student data and stay in the ignored
`debug_output/` directory. The comparison command exits nonzero on unexpected
changes and records every change in `comparison.json`. Missing sections alone
are not errors: the source reports legitimately contain different student sets.

Focused checks:

```bash
venv_pathwayextractor/bin/python -m unittest \
  pathway_extractor.tests.test_name_repair \
  pathway_extractor.tests.test_name_benchmark_comparison
venv_pathwayextractor/bin/python scripts/reproduce_wrapped_name.py
venv_pathwayextractor/bin/python scripts/reproduce_wrapped_name.py --repair-wrapped-names
```
