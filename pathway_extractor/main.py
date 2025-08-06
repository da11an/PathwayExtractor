from pathlib import Path
from shutil import rmtree
from pathway_extractor.extractor import extract_records_from_zip
from pathway_extractor.generate_messages import generate_message
from pathway_extractor.parsers.utils import invert_student_data
from pathway_extractor.utils import get_zip_file
from collections import Counter


downloads_dir = Path.home() / "Downloads"
zip_file = get_zip_file(download_dir=downloads_dir)

class_page_records = extract_records_from_zip(
    zip_path=str(zip_file),
    max_files=None,
    filename_filter=None,
    debug=False
)

regions = Counter([
    item.get('class_info', {}).get('region', "⚠️ Filename parsing issue: " + item.get('file')) 
    for item in class_page_records
])
print("🔍 Class count by region: \n ------------------------- \n")
for region, count in regions.items():
    print(f"{region}: {count}")
print("End of class count by region report \n ------------------------- \n")

class_student_records = [invert_student_data(record) for record in class_page_records]

output_dir = downloads_dir / zip_file.name.replace(".zip", "")
if output_dir.exists():
    rmtree(output_dir) # remove old results
output_dir.mkdir(parents=True, exist_ok=True)

for record in class_student_records:
    generate_message(record, output_dir)