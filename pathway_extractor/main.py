from pathlib import Path
from shutil import rmtree
from pathway_extractor.extractor import extract_records_from_zip
from pathway_extractor.generate_messages import generate_message
from pathway_extractor.parsers.utils import invert_student_data
from pathway_extractor.utils import get_zip_file
from pathway_extractor.analytics import calculate_class_averages, plot_class_averages_paginated
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
averages = calculate_class_averages(class_student_records)
figures = plot_class_averages_paginated(averages, classes_per_page=55)
for i, fig in enumerate(figures):
    fig.savefig(f'class_averages_page_{i+1:02d}.png', dpi=300, bbox_inches='tight')

# Ensure cross-platform compatibility for output directory creation
zip_filename = zip_file.name
output_dir_name = zip_filename.replace(".zip", "")
output_dir = downloads_dir / output_dir_name

# Debug information for troubleshooting
print(f"📁 Creating output directory:")
print(f"   Downloads dir: {downloads_dir}")
print(f"   Zip filename: {zip_filename}")
print(f"   Output dir name: {output_dir_name}")
print(f"   Full output path: {output_dir}")

if output_dir.exists():
    print(f"   Removing existing directory: {output_dir}")
    rmtree(output_dir) # remove old results

output_dir.mkdir(parents=True, exist_ok=True)
print(f"   ✅ Output directory created: {output_dir}")

for record in class_student_records:
    generate_message(record, output_dir)