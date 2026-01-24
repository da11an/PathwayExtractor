import json
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from pathway_extractor.html_to_png import save_html_as_png
from pathway_extractor.utils import sanitize_filename
from pathway_extractor.message_generator import generate_encouraging_message, analyze_student_progress

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
    """
    Generate HTML for student progress report PNG.
    
    NOTE: Encouraging messages are NOT included in the PNG. 
    They are only in the separate class encouragement HTML document.
    """
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

    # Get first name for greeting
    first_name = student_name.split()[0] if student_name else "Friend"
    
    html += f"""
        <p class="emoji-note">😃 <strong>Hi, {first_name}!</strong> 
        Here is the most recent update on units you have completed in the Proficiency section of the EC3 learning app.
        Press forward with faith in every footstep to reach your goals.</p>
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

    # Track class folder for encouragement HTML (all students in same class go to same folder)
    class_folder = None
    student_messages = []  # Collect messages for the class HTML
    
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
        
        # Generate PNG (no encouraging message - that's in the separate HTML)
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
        
        # Track the class folder (same for all students in this class)
        if class_folder is None:
            class_folder = student_dir

        # Sanitize student name for filename to avoid invalid characters
        safe_student_name = sanitize_filename(student_name, max_length=200)
        output_png_path = student_dir / f"{safe_student_name}.png"
        
        save_html_as_png(html, output_png_path, width=700, height=300)
        
        # Generate encouraging message and collect for class HTML
        encouraging_message = generate_encouraging_message(student_name, data)
        patterns = analyze_student_progress(data)
        context = patterns.get("_context", {})
        
        student_messages.append({
            "name": student_name,
            "message": encouraging_message,
            "block_total": context.get("total", 0),
            "alltime_total": context.get("total_alltime", 0),
            "certified_count": context.get("certified_count", 0),
            "is_pathway_ready": context.get("certified_count", 0) == 6,
        })
    
    # Generate the class encouragement HTML document
    if class_folder and student_messages:
        generate_class_encouragement_html(student_messages, class_info, class_folder)


def generate_class_encouragement_html(student_messages: list, class_info: dict, output_dir: Path) -> Path:
    """
    Generate HTML document with encouragement messages for all students in a class.
    
    This document is designed for instructors to copy/paste messages into personal communications.
    
    Args:
        student_messages: List of dicts with 'name', 'message', 'block_total', 'alltime_total', 
                         'certified_count', 'is_pathway_ready'
        class_info: Class metadata (facilitators, day, time, region, etc.)
        output_dir: The class folder where PNG files are saved
    
    Returns:
        Path to generated encouragement_messages.html file
    """
    # Build class title from info
    facilitators = class_info.get("facilitators", ["Unknown"])
    facilitator = facilitators[0] if facilitators else "Unknown"
    day = class_info.get("day", "")
    time = class_info.get("time", "")
    region = class_info.get("region", "")
    
    class_title = f"{facilitator} - {day} {time}"
    if region:
        class_title = f"{region}: {class_title}"
    
    generated_date = datetime.now().strftime("%B %d, %Y")
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Student Encouragement Messages - {facilitator}</title>
    <style>
        * {{
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #fafafa;
            color: #333;
        }}
        h1 {{
            color: #2c5282;
            border-bottom: 2px solid #4299e1;
            padding-bottom: 10px;
            margin-bottom: 5px;
        }}
        .meta {{
            color: #718096;
            font-size: 0.9em;
            margin-bottom: 30px;
        }}
        .student-card {{
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 15px 20px;
            margin-bottom: 15px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .student-card.pathway-ready {{
            border-left: 4px solid #48bb78;
            background: linear-gradient(to right, #f0fff4, white);
        }}
        .student-name {{
            font-size: 1.1em;
            font-weight: 600;
            color: #2d3748;
            margin-bottom: 8px;
        }}
        .message {{
            font-size: 1em;
            color: #4a5568;
            line-height: 1.5;
            padding: 10px;
            background: #f7fafc;
            border-radius: 4px;
            border-left: 3px solid #4299e1;
            margin-bottom: 10px;
        }}
        .stats {{
            font-size: 0.85em;
            color: #718096;
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }}
        .stat {{
            background: #edf2f7;
            padding: 3px 8px;
            border-radius: 4px;
        }}
        .stat.highlight {{
            background: #c6f6d5;
            color: #276749;
        }}
        .copy-hint {{
            font-size: 0.8em;
            color: #a0aec0;
            margin-top: 20px;
            text-align: center;
            font-style: italic;
        }}
        .emoji {{
            margin-right: 5px;
        }}
    </style>
</head>
<body>
    <h1>📚 Student Encouragement Messages</h1>
    <p class="meta">Class: {class_title}<br>Generated: {generated_date}</p>
"""
    
    # Sort students alphabetically
    student_messages_sorted = sorted(student_messages, key=lambda x: x["name"].lower())
    
    for student in student_messages_sorted:
        name = student["name"]
        message = student["message"]
        block_total = student["block_total"]
        alltime_total = student["alltime_total"]
        certified_count = student["certified_count"]
        is_pathway_ready = student["is_pathway_ready"]
        
        # Card styling based on achievement
        card_class = "student-card pathway-ready" if is_pathway_ready else "student-card"
        
        # Emoji for special achievements
        name_emoji = "🎓 " if is_pathway_ready else "👤 "
        achievement_emoji = " ⭐" if certified_count >= 4 else ""
        
        # Stats display
        completion_stat_class = "stat highlight" if certified_count >= 4 else "stat"
        
        html += f"""
    <div class="{card_class}">
        <div class="student-name">{name_emoji}{name}{achievement_emoji}</div>
        <div class="message">💬 {message}</div>
        <div class="stats">
            <span class="stat">This Block: {block_total} units</span>
            <span class="stat">All-Time: {alltime_total} units</span>
            <span class="{completion_stat_class}">Completion: {certified_count}/6 skills</span>
        </div>
    </div>
"""
    
    html += """
    <p class="copy-hint">Tip: Select and copy individual messages to personalize your communications with students.</p>
</body>
</html>
"""
    
    # Write the HTML file
    output_path = output_dir / "encouragement_messages.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"   📝 Created encouragement messages: {output_path}")
    
    return output_path


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
