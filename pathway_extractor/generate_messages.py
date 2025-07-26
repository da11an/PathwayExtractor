import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


SKILLS = ["grammar", "listen", "read", "speak", "vocabulary", "write"]

def draw_student_summary(student, output_folder: Path):
    name = student["student_name"]
    level = student["level"]
    units = student["units"]
    avg = student["average_units_per_week"]
    message = student["message"]

    img_width, img_height = 700, 400
    padding = 20
    row_height = 40
    column_width = 100

    # Create image
    img = Image.new("RGB", (img_width, img_height), "white")
    draw = ImageDraw.Draw(img)

    # Load fonts
    try:
        font_title = ImageFont.truetype("arial.ttf", 24)
        font = ImageFont.truetype("arial.ttf", 20)
        font_small = ImageFont.truetype("arial.ttf", 16)
    except OSError:
        print("⚠️ Could not load 'arial.ttf'. Falling back to default font.")
        font_title = ImageFont.load_default()
        font = ImageFont.load_default()
        font_small = ImageFont.load_default()


    # Title
    draw.text((padding, padding), f"{name}", font=font_title, fill="black")

    # Skill headers
    y_start = padding + 40
    draw.text((padding, y_start), "Skill", font=font, fill="black")
    for i, skill in enumerate(SKILLS):
        draw.text((padding + (i + 1) * column_width, y_start), skill.capitalize(), font=font, fill="black")

    # Levels row
    y_levels = y_start + row_height
    draw.text((padding, y_levels), "Level", font=font, fill="black")
    for i, skill in enumerate(SKILLS):
        draw.text((padding + (i + 1) * column_width, y_levels), str(level.get(skill, 0)), font=font, fill="black")

    # Units row
    y_units = y_levels + row_height
    draw.text((padding, y_units), "Units", font=font, fill="black")
    for i, skill in enumerate(SKILLS):
        draw.text((padding + (i + 1) * column_width, y_units), str(units.get(skill, 0)), font=font, fill="black")

    # Average
    y_avg = y_units + row_height + 10
    draw.text((padding, y_avg), f"Avg units/week: {avg}", font=font, fill="black")

    # Message
    y_msg = y_avg + row_height
    draw.text((padding, y_msg), message, font=font_small, fill="black")

    # Save image
    filename = f"{name.replace(' ', '_')}.png"
    output_path = output_folder / filename
    img.save(output_path)
    print(f"Saved {output_path}")


def main(summaries_jsonl: str, output_dir: str):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    with open(summaries_jsonl, "r", encoding="utf-8") as f:
        for line in f:
            student = json.loads(line)
            draw_student_summary(student, output_path)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate PNG summary images from student summaries.")
    parser.add_argument("summaries_jsonl", help="Input JSONL file of student summaries")
    parser.add_argument("--output-dir", default="student_images", help="Directory to write PNG files")
    args = parser.parse_args()

    main(args.summaries_jsonl, args.output_dir)

# python pathway_extractor\tests\generate_messages.py student_summaries.jsonl --output-dir summary_images
