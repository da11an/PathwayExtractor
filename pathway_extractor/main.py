from pathlib import Path
from shutil import rmtree
import argparse
import json
import io
from zipfile import ZipFile
import pdfplumber
from pathway_extractor.extractor import extract_records_from_zip
from pathway_extractor.generate_messages import generate_message
from pathway_extractor.parsers.utils import invert_student_data
from pathway_extractor.utils import get_zip_file
from pathway_extractor.analytics import calculate_class_averages, plot_class_averages_paginated
from pathway_extractor.config_loader import load_config
from pathway_extractor.config_generator import analyze_pdf_for_tables, generate_config_file
from collections import Counter


def main():
    parser = argparse.ArgumentParser(description="Extract and process pathway data from PDF zip files")
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to extraction configuration JSON file (default: uses format_v1.json)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output"
    )
    args = parser.parse_args()
    
    downloads_dir = Path.home() / "Downloads"
    zip_file = get_zip_file(download_dir=downloads_dir)
    
    # If no config provided, auto-generate one from the ZIP file
    if args.config is None:
        print("🔧 No config provided. Auto-generating configuration from ZIP file...")
        
        # Load generator config
        config_dir = Path(__file__).parent / "configs"
        generator_config_path = config_dir / "generator_config.json"
        
        if not generator_config_path.exists():
            print(f"❌ Generator config not found: {generator_config_path}")
            print("   Please create a generator_config.json file first, or provide a config with --config")
            return
        
        with open(generator_config_path, 'r') as f:
            generator_config = json.load(f)
        
        # Extract first PDF from ZIP for analysis
        with ZipFile(zip_file, 'r') as zf:
            pdf_names = [n for n in zf.namelist() if n.lower().endswith('.pdf')]
            
            if not pdf_names:
                print("❌ No PDF files found in ZIP")
                return
            
            selected_pdf_name = pdf_names[0]
            print(f"   Analyzing PDF: {selected_pdf_name}")
            
            # Read PDF data from ZIP
            with zf.open(selected_pdf_name) as pdf_data:
                pdf_file = io.BytesIO(pdf_data.read())
        
        # Analyze PDF and generate config
        found_configs = analyze_pdf_for_tables(pdf_file, generator_config, selected_pdf_name)
        
        if not found_configs:
            print("\n❌ Could not generate configuration. No tables found in PDF.")
            print("   Please provide a config manually with --config")
            return
        
        # Generate temporary config file
        auto_config_path = config_dir / "format_auto_generated.json"
        generate_config_file(found_configs, str(auto_config_path), "format_auto_generated", 
                           "Auto-generated configuration from ZIP analysis")
        
        # Use the generated config
        args.config = str(auto_config_path)
        print(f"✅ Using auto-generated config: {auto_config_path}")
    
    # Load configuration
    config = load_config(args.config)
    print(f"📋 Using extraction format: {config.format_name}")
    if config.description:
        print(f"   {config.description}")
    
    # Create debug directory if debug mode is enabled
    debug_dir = None
    if args.debug:
        zip_filename = zip_file.name
        output_dir_name = zip_filename.replace(".zip", "")
        debug_dir = Path.cwd() / "debug_output" / output_dir_name
        debug_dir.mkdir(parents=True, exist_ok=True)
        print(f"🐛 Debug mode enabled. Debug artifacts will be saved to: {debug_dir}")
    
    class_page_records = extract_records_from_zip(
        zip_path=str(zip_file),
        max_files=None,
        filename_filter="Alumande",
        debug=args.debug,
        config=config,
        debug_dir=debug_dir
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
    output_location = Path.home() / "OneDrive" / "EC3 Learner Images"
    output_dir = output_location / output_dir_name

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


if __name__ == "__main__":
    main()