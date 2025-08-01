import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from pathway_extractor.html_to_png import save_html_as_png

SKILLS = ["grammar", "listen", "read", "speak", "vocabulary", "write"]

def output_folder_structure(student, output_folder: Path):
    folder_level_1 = student["class_info"]["region"] + "_" + student["class_info"]["type"]
    folder_level_2 = (student["class_info"]["facilitators"][0] + "_" + 
                      student["class_info"]["day"] + "_" + 
                      student["class_info"]["time"])
    
    # Create the directory structure for this student
    student_dir = output_folder / folder_level_1 / folder_level_2
    student_dir.mkdir(parents=True, exist_ok=True)

    return student_dir


def generate_progress_report_html(student_name, levels, units, weekly_units):
    skills = ["Grammar", "Listening", "Reading", "Speaking", "Vocabulary", "Writing"]
    weeks = list(range(1, len(weekly_units) + 1))
    max_week_val = max(weekly_units.values()) if weekly_units else 0
    average_weekly_units = round(sum(weekly_units.values()) / max(len(weekly_units), 1), 1)

    html = """
    <html>
    <head>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 20px;
                background-color: #f9f9f9;
            }
            table {
                border-collapse: collapse;
                width: 100%;
                margin-bottom: 20px;
                background-color: white;
            }
            th {
                background-color: #e0e0e0;
                color: #333;
                font-weight: bold;
            }
            tr:nth-child(even) td {
                background-color: #f2f2f2;
            }
            th, td {
                border: 1px solid #ccc;
                padding: 10px;
                text-align: center;
            }
            .bold { font-weight: bold; }
            .red { color: red; }
            .emoji-note {
                font-size: 16px;
                margin-top: 20px;
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

    # Level row (convert -1 to "-" for unassessed skills)
    html += '<tr><td class="bold">Level</td>'
    for skill in skills:
        level = levels.get(skill.lower(), -1)
        html += f"<td>{'-' if level == -1 else level}</td>"
    html += "</tr>"

    # Units row
    html += '<tr><td class="bold">Units</td>'
    for skill in skills:
        html += f"<td>{units.get(skill.lower(), 0)}</td>"
    html += "</tr>"
    html += "</table>"

    html += "<table>"

    # Weeks header row
    html += f'<tr><th>Weeks 1-{len(weeks)}</th>'
    for week in weeks:
        html += f"<th>{week}</th>"
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

    html += f"""
        </table>

        <p class="bold">Your Average Units Completed Each Week of The Semester: 
            <span class="red bold">{average_weekly_units:.1f}</span>
        </p>

        <p class="emoji-note">😃 <strong>Good morning, {student_name}!</strong> 
        Here is the most recent update on units you have completed in the English learning app.
        If you have a question about the chart and what it means, please pick up your phone and call me.</p>
    </body>
    </html>
    """

    return html


def main(summaries_jsonl: str, output_dir: str):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    with open(summaries_jsonl, "r", encoding="utf-8") as f:
        for line in f:
            class_record = json.loads(line)
            class_info = class_record.get("class_info", {})
            class_file = class_record.get("file", "unknown filename")

            students = class_record.get("students", {})
            if not students:
                print(f"⚠️ No students found in class: {class_file}")
                continue
            else:
                print(f"Generating reports for {len(students)} students in class: {class_file}")

            for student_name, data in students.items():
                weekly = data.get("weekly_submissions", {})
                skill_units = data.get("submissions_by_skill", {})
                levels = data.get("skill_scores", {})

                weekly_units = {int(k.split("_")[1]): v for k, v in weekly.items() if k.startswith("week_")}
                
                html = generate_progress_report_html(
                    student_name=student_name,
                    levels=levels,
                    units=skill_units,
                    weekly_units=weekly_units,
                )

                # Create student output folder
                student_dir = output_folder_structure({
                    "student_name": student_name,
                    "class_info": class_info
                }, output_path)

                save_html_as_png(html, student_dir / f"{student_name}.png", width=700, height=300)



# def main(summaries_jsonl: str, output_dir: str):
#     output_path = Path(output_dir)
#     # Create the main output directory
#     output_path.mkdir(parents=True, exist_ok=True)

#     with open(summaries_jsonl, "r", encoding="utf-8") as f:
#         for line in f:
#             student = json.loads(line)
#             print(student)
#             html = generate_progress_report_html(
#                 student_name=student["student_name"],
#                 levels=student["level"],
#                 units=student["units"],
#                 weekly_units={i+1: val for i, val in enumerate(student["weekly_units"])},
#             )
#             student_dir = output_folder_structure(student, output_path)
#             save_html_as_png(html, student_dir / f"{student['student_name']}.png", width=700, height=300)


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