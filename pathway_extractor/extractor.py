import re
import io
import json
from zipfile import ZipFile
import pdfplumber
from tqdm import tqdm
import argparse

from pathway_extractor.parsers.page_2 import parse_page_2_table, test_row as test_row_page_2
from pathway_extractor.parsers.page_3 import parse_page_3_table, test_row as test_row_page_3
from pathway_extractor.parsers.page_4 import parse_page_4_table, test_row as test_row_page_4
from pathway_extractor.parsers.filename import parse_filename

PAGES_TO_GRAB = [1, 2, 3]  # zero-based index for pages 2,3,4


def parse_record(file_name: str, page_tables: dict) -> dict:
    parsed = {
        "file": file_name,
        **parse_filename(file_name),
        **parse_page_2_table(page_tables.get("page2_text", [])),
        **parse_page_3_table(page_tables.get("page3_text", [])),
        **parse_page_4_table(page_tables.get("page4_text", [])),
    }
    return parsed



def process_zip(zip_path: str, jsonl_out: str, max_files: int = None):
    with ZipFile(zip_path, "r") as zf, \
         open(jsonl_out, "w", encoding="utf-8") as jsonl_f:

        pdf_names = [n for n in zf.namelist() if n.lower().endswith(".pdf")]

        # Optionally limit the number of files
        if max_files is not None:
            pdf_names = pdf_names[:max_files]

        for name in tqdm(pdf_names, desc="Processing PDFs"):
            try:
                with zf.open(name) as f:
                    data = f.read()
                with pdfplumber.open(io.BytesIO(data)) as pdf:
                    page_tables = {}
                    for idx, label, row_test in zip(
                            PAGES_TO_GRAB,
                            ["page2_text", "page3_text", "page4_text"],
                            [test_row_page_2, test_row_page_3, test_row_page_4]
                        ):
                        if idx < len(pdf.pages):
                            table = pdf.pages[idx].extract_table(
                                table_settings={
                                    "vertical_strategy": "text", 
                                    "horizontal_strategy": "text"
                                }
                            ) or []
                            print("name", name)
                            print("label", label)
                            test_result = [row_test(row) for row in table]
                            print(test_result)
                            if not any(test_result):
                                print("Try backup parsing method!!!")
                        else:
                            table = []
                        page_tables[label] = table

                    rec = parse_record(name, page_tables)

                jsonl_f.write(json.dumps(rec, ensure_ascii=False) + "\n")

            except Exception as e:
                err_obj = {"file": name, "error": str(e)}
                jsonl_f.write(json.dumps(err_obj, ensure_ascii=False) + "\n")

    print(f"Done. JSONL output -> {jsonl_out}")


def main():
    parser = argparse.ArgumentParser(description="Extract pages 2-4 from PDFs in a ZIP and write to JSONL.")
    parser.add_argument("zip_path", help="Path to the ZIP containing PDFs")
    parser.add_argument("--jsonl-out", default="out.jsonl", help="JSONL output file (default: out.jsonl)")
    args = parser.parse_args()

    process_zip(args.zip_path, args.jsonl_out)


if __name__ == "__main__":
    main()
