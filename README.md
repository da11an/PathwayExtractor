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

## How to Run

From vscode just hit the play button for main.py. (It is necessary to have your python environment (including running `post_install.py`) created and activated prior to running main.py.) 

```bash
python main.py
```


By default, main.py will attempt to load a zip file as entered in the file. If no ZIP is found, a file dialog will open to let the user choose one.

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