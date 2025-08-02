from pathlib import Path
from pathway_extractor.extractor import extract_records_from_zip
from pathway_extractor.generate_messages import generate_message
from pathway_extractor.parsers.utils import invert_student_data

# Setup test paths
from tkinter import filedialog
zip_file = Path(filedialog.askopenfilename(
    title="Select ZIP file of EC3 PDF Reports",
    filetypes=[("ZIP files", "*.zip")]
))

class_page_records = extract_records_from_zip(str(zip_file), max_files=None, filename_filter=None)
class_student_records = [invert_student_data(record) for record in class_page_records]

output_dir = Path("output")
output_dir.mkdir(parents=True, exist_ok=True)

for record in class_student_records:
    generate_message(record, output_dir)