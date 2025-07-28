from pathlib import Path
from pathway_extractor.extractor import process_zip

# Setup test paths
zip_file = Path("/home/dallan/Downloads/OneDrive_1_7-25-2025.zip")
jsonl_out = Path("test_output.jsonl")
filename_filter = None
# filename_filter = "Utah EC3 - Sandy, IP, Sunday, 03_00 PM - Hungate, Hungate.pdf"

# Run the processor
process_zip(str(zip_file), str(jsonl_out), max_files=50, filename_filter=filename_filter)
