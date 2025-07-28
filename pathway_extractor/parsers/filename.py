import os
import re

def parse_filename(file_name: str) -> dict:
    base = os.path.splitext(file_name)[0].strip()

    # Split on final ' - ' to separate facilitator section
    if " - " not in base:
        raise ValueError(f"Missing ' - ' in filename: {file_name}")

    metadata_part, facilitators_part = base.rsplit(" - ", 1)
    facilitators = [f.strip() for f in facilitators_part.split(",") if f.strip()]

    # Pattern for virtual class (comma-separated, no site)
    virtual_match = re.match(
        r"^(?P<location>\w+)\s+(?P<class_code>\w+),\s*(?P<type_code>\w+),\s*(?P<class_day>\w+),\s*(?P<class_time>[\d_]+ [AP]M)$",
        metadata_part
    )

    if virtual_match:
        return {
            **virtual_match.groupdict(),
            "site": None,
            "facilitators": facilitators,
        }

    # Pattern for in-person class (site allowed to include commas)
    in_person_match = re.match(
        r"^(?P<location>\w+)\s+(?P<class_code>\w+)\s*-\s*(?P<site>.+),\s*(?P<type_code>\w+),\s*(?P<class_day>\w+),\s*(?P<class_time>[\d_]+ [AP]M)$",
        metadata_part
    )

    if in_person_match:
        return {
            **in_person_match.groupdict(),
            "facilitators": facilitators,
        }

    raise ValueError(f"Unrecognized filename format: {file_name}")
