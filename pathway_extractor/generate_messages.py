import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from pathway_extractor.html_to_png import save_html_as_png

SKILLS = ["grammar", "listen", "read", "speak", "vocabulary", "write"]

def draw_student_summary(student, output_folder: Path):
    name = student["student_name"]
    level = student["level"]
    units = student["units"]
    avg = student["average_units_per_week"]
    message = student["message"]
    folder_level_1 = student["class_info"]["region"] + "_" + student["class_info"]["type"]
    folder_level_2 = (student["class_info"]["facilitators"][0] + "_" + 
                      student["class_info"]["day"] + "_" + 
                      student["class_info"]["time"])

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

    # Create the directory structure for this student
    student_dir = output_folder / folder_level_1 / folder_level_2
    student_dir.mkdir(parents=True, exist_ok=True)
    
    # Save image
    filename = f"{name.replace(' ', '_')}.png"
    output_path = student_dir / filename
    img.save(output_path)
    print(f"Saved {output_path}")


def generate_progress_report_html(student_name, levels, units, weekly_units):
    skills = ["Grammar", "Listening", "Reading", "Speaking", "Vocabulary", "Writing"]
    weeks = list(range(1, len(weekly_units) + 1))
    max_week_val = max(weekly_units.values()) if weekly_units else 0
    average_weekly_units = sum(weekly_units.values()) / len(weekly_units)

    html = """
    <html>
    <head>
        <style>
            table {
                border-collapse: collapse;
                width: 100%;
                font-family: Arial, sans-serif;
            }
            th, td {
                border: 1px solid black;
                padding: 8px;
                text-align: center;
            }
            .bold { font-weight: bold; }
            .red { color: red; }
            .emoji-note {
                font-size: 16px;
                padding-top: 10px;
            }
        </style>
    </head>
    <body>
        <table>
            <tr>
                <th>Skill</th>
    """
    for skill in skills:
        html += f"<th>{skill}</th>"
    html += "</tr>"

    # Level row
    html += '<tr><td class="bold">Level</td>'
    for skill in skills:
        html += f"<td>{levels.get(skill.lower(), 0)}</td>"
    html += "</tr>"

    # Units row
    html += '<tr><td class="bold">Units</td>'
    for skill in skills:
        html += f"<td>{units.get(skill.lower(), 0)}</td>"
    html += "</tr>"
    html += "</table>"
    html += "<br>"
    html += "<table>"

    # Weeks row
    html += f'<tr><td class="bold">Weeks 1-{len(weeks)}</td>'
    for week in weeks:
        html += f"<td>{week}</td>"
    html += "</tr>"

    # Weekly Units row
    html += '<tr><td class="bold">Units</td>'
    for week in weeks:
        val = weekly_units.get(week, 0)
        if val == max_week_val and val > 0:
            html += f'<td><span class="red">{val}</span></td>'
        else:
            html += f"<td>{val}</td>"
    html += "</tr>"

    html += """
        </table>

        <p class="bold">Your Average Units Completed Each Week of The Semester: <span class="red bold">""" + f"{average_weekly_units:.1f}" + """</span></p>

        <p class="emoji-note">😃 Good morning, """ + student_name + """! Here is the most recent update on units you have completed in the English learning app. If you have a question about the chart and what it means please pick up your phone and call me.</p>
    </body>
    </html>
    """

    return html


def main(summaries_jsonl: str, output_dir: str):
    output_path = Path(output_dir)
    # Create the main output directory
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

html = generate_progress_report_html(
    student_name="Angie",
    levels={"grammar": 0, "listening": 0, "reading": 0, "speaking": 0, "vocabulary": 2, "writing": 2},
    units={"grammar": 11, "listening": 1, "reading": 3, "speaking": 0, "vocabulary": 6, "writing": 2},
    weekly_units={1: 0, 2: 17, 3: 6, 4: 10, 5: 39, 6:12, 7:2},
)

# with open("angie_report.html", "w", encoding="utf-8") as f:
#     f.write(html)

save_html_as_png(html, "angie_report.png", width=700, height=300)