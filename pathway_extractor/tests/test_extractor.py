from pathlib import Path
from pathway_extractor.extractor import process_zip

# Setup test paths
zip_file = Path("C:/Users/dlpri/Downloads/OneDrive_1_7-25-2025.zip")
jsonl_out = Path("test_output.jsonl")

# Run the processor
process_zip(str(zip_file), str(jsonl_out), max_files=5)
