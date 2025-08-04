from pathlib import Path
from shutil import rmtree
from pathway_extractor.extractor import extract_records_from_zip
from pathway_extractor.generate_messages import generate_message
from pathway_extractor.parsers.utils import invert_student_data


# Provide a default zip file path or to use file dialog set to: None
zip_file = Path.home() / "Downloads" / "OneDrive_1_7-25-2025.zip"

if zip_file is None or not zip_file.exists():
    # Setup path selection dialog
    from tkinter import filedialog
    zip_file = Path(filedialog.askopenfilename(
        title="Select ZIP file of EC3 PDF Reports",
        filetypes=[("ZIP files", "*.zip")]
    ))

class_page_records = extract_records_from_zip(
    zip_path=str(zip_file),
    max_files=None,
    filename_filter=None,
    debug=False
)
class_student_records = [invert_student_data(record) for record in class_page_records]

output_dir = Path("output")
rmtree(output_dir) # remove old results
output_dir.mkdir(parents=True, exist_ok=True)

for record in class_student_records:
    generate_message(record, output_dir)