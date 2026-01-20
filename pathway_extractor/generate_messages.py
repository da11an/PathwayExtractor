import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from pathway_extractor.html_to_png import save_html_as_png
from pathway_extractor.utils import sanitize_filename

SKILLS = ["grammar", "listen", "read", "speak", "vocabulary", "write"]

def output_folder_structure(student, output_folder: Path):
    # Sanitize folder names to avoid invalid characters
    region = sanitize_filename(student["class_info"]["region"], max_length=100)
    class_type = sanitize_filename(student["class_info"]["type"], max_length=100)
    folder_level_1 = f"{region}_{class_type}"
    
    facilitator = sanitize_filename(student["class_info"]["facilitators"][0] if student["class_info"]["facilitators"] else "Unknown", max_length=50)
    day = sanitize_filename(student["class_info"]["day"], max_length=20)
    time = sanitize_filename(student["class_info"]["time"], max_length=20)
    folder_level_2 = f"{facilitator}_{day}_{time}"
    
    # Create the directory structure for this student
    student_dir = output_folder / folder_level_1 / folder_level_2
    student_dir.mkdir(parents=True, exist_ok=True)

    return student_dir


def generate_progress_report_html(student_name: str, facilitators: list, levels: dict, units: dict, weekly_units: dict):
    skills = ["Grammar", "Listening", "Reading", "Speaking", "Vocabulary", "Writing"]
    weeks = list(range(1, len(weekly_units) + 1))
    # Ensure all values are integers (handle cases where clean_value might return strings)
    weekly_units_ints = {k: int(v) if isinstance(v, (int, str)) and str(v).strip().lstrip('-').isdigit() else 0 
                         for k, v in weekly_units.items()}
    max_week_val = max(weekly_units_ints.values()) if weekly_units_ints else 0
    average_weekly_units = round(sum(weekly_units_ints.values()) / max(len(weekly_units_ints), 1), 1)

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
    """

    html += f"""
        <p class="emoji-note">😃 <strong>Hi, {student_name.split()[0]}!</strong> 
        Here is the most recent update on units you have completed in the Proficiency section of the EC3 learning app.
        "Press forward with faith in every footstep" to reach your goals.</p>
    """

    html += f'<div style="display: flex; justify-content: space-between; margin: 20px 0;"><div><strong>{student_name}</strong></div><div><small>{", ".join(facilitators)}</small></div></div>'

    html += """
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
        val = weekly_units_ints.get(week, 0)
        if val == max_week_val and val > 0:
            html += f'<td><span class="red">{val}</span></td>'
        else:
            html += f"<td>{val}</td>"
    html += "</tr>"

    html += f"""
        </table>

        <p class="bold">Your Average Units Completed Each Week of The Block: 
            <span class="red bold">{average_weekly_units:.1f}</span>
        </p>
    </body>
    </html>
    """

    return html


def generate_message(class_record: dict, output_path: Path):
    class_info = class_record.get("class_info", {})
    class_file = class_record.get("file", "unknown filename")
    pdf_size = class_record.get("pdf_size")

    students = class_record.get("students", {})
    if not students and pdf_size > 150000: # set based on examining typical PDF sizes when there are no students
        print(f"❌ No students found in class possibly due to parsing error: {class_file} (PDF size={pdf_size} bytes)")
    elif not students:
        print(f"⚠️ No students found in class: {class_file} (PDF size={pdf_size} bytes)")
        return
    else:
        print(f"Generating reports for {len(students)} students in class: {class_file}")

    for student_name, data in students.items():
        weekly = data.get("weekly_submissions", {})
        skill_units = data.get("submissions_by_skill", {})
        levels = data.get("skill_scores", {})

        # Extract weekly units and ensure values are integers
        weekly_units = {}
        for k, v in weekly.items():
            if k.startswith("week_"):
                week_num = int(k.split("_")[1])
                # Convert to int, defaulting to 0 if conversion fails
                try:
                    weekly_units[week_num] = int(v) if not isinstance(v, int) else v
                except (ValueError, TypeError):
                    weekly_units[week_num] = 0
        
        html = generate_progress_report_html(
            student_name=student_name,
            facilitators=class_info.get("facilitators", []),
            levels=levels,
            units=skill_units,
            weekly_units=weekly_units,
        )

        # Create student output folder
        student_dir = output_folder_structure({
            "student_name": student_name,
            "class_info": class_info
        }, output_path)

        # Sanitize student name for filename to avoid invalid characters
        safe_student_name = sanitize_filename(student_name, max_length=200)
        output_png_path = student_dir / f"{safe_student_name}.png"
        
        save_html_as_png(html, output_png_path, width=700, height=300)


def main(summaries_jsonl: str, output_dir: str):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    with open(summaries_jsonl, "r", encoding="utf-8") as f:
        for line in f:
            class_record = json.loads(line)
            generate_message(class_record, output_path)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate PNG summary images from student summaries.")
    parser.add_argument("summaries_jsonl", help="Input JSONL file of student summaries")
    parser.add_argument("--output-dir", default="student_images", help="Directory to write PNG files")
    args = parser.parse_args()

    main(args.summaries_jsonl, args.output_dir)

# python pathway_extractor\tests\generate_messages.py student_summaries.jsonl --output-dir summary_images
