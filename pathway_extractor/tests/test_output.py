import json
from pathlib import Path
from pathway_extractor.parsers.utils import invert_student_data

def main(input_jsonl: str, output_jsonl: str):
    input_path = Path(input_jsonl)
    output_path = Path(output_jsonl)

    all_summaries = []

    with input_path.open("r", encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            inverted = invert_student_data(record)
            all_summaries.append(inverted)

    with output_path.open("w", encoding="utf-8") as f:
        for summary in all_summaries:
            f.write(json.dumps(summary, ensure_ascii=False) + "\n")

    print(f"Wrote {len(all_summaries)} class summaries to {output_jsonl}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate student summary output from extracted PDF data.")
    parser.add_argument("input_jsonl", help="Path to input JSONL file with page2/3/4 data")
    parser.add_argument("--output-jsonl", default="student_summaries.jsonl", help="Path to write output summaries")
    args = parser.parse_args()

    main(args.input_jsonl, args.output_jsonl)
