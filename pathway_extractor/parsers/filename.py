import os
import re

def parse_filename(file_name: str) -> dict:
    # Remove ".pdf" and normalize spaces
    base = os.path.splitext(file_name)[0].strip()

    # Split into left and right of the " - " separator
    if " - " not in base:
        raise ValueError(f"Filename missing ' - ' separator: {file_name}")
    
    left, right = base.split(" - ", 1)

    # Left side: <Location> <Class Code>, <Type Code>, <Class Day>, <Class Time>
    left_parts = [p.strip() for p in left.split(",")]
    if len(left_parts) != 4:
        raise ValueError(f"Left part does not have 4 comma-separated values: {left_parts}")
    
    location_and_code = left_parts[0].rsplit(" ", 1)
    if len(location_and_code) != 2:
        raise ValueError(f"Location and class code format issue: {left_parts[0]}")
    
    location = location_and_code[0]
    class_code = location_and_code[1]
    type_code = left_parts[1]
    class_day = left_parts[2]
    class_time = left_parts[3]

    # Right side: facilitators, possibly multiple, separated by ", "
    facilitators = [f.strip() for f in right.split(",") if f.strip()]

    return {
        "location": location,
        "class_code": class_code,
        "type_code": type_code,
        "class_day": class_day,
        "class_time": class_time,
        "facilitators": facilitators
    }
