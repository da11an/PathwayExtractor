import os
import re

def parse_filename(file_name: str) -> dict:
    base = os.path.splitext(file_name)[0].strip()

    if " - " not in base:
        raise ValueError(f"Missing ' - ' in filename: {file_name}")

    metadata_part, facilitators_part = base.rsplit(" - ", 1)
    facilitators = [f.strip() for f in facilitators_part.split(",") if f.strip()]

    def clean_region(region):
        return region.replace("Virtual", "").strip()

    # In-person format with location that may include commas
    in_person_match = re.match(
        r"^(?P<region>.+?)\s+EC3?\s*-\s*(?P<location>.+?),\s*(?P<type>IP|In\s?Person),\s*(?P<day>\w+),\s*(?P<time>[\d_]+ [AP]M)$",
        metadata_part
    )
    if in_person_match:
        data = in_person_match.groupdict()
        return {"class_info": {
            "region": clean_region(data["region"]),
            "location": data["location"],
            "type": "In Person",  # Standardize
            "day": data["day"],
            "time": data["time"],
            "facilitators": facilitators
        }}

    # Virtual format with comma-separated elements (e.g., Utah EC3, V, ...)
    virtual_comma_match = re.match(
        r"^(?P<region>.+?)\s+EC3?,\s*[A-Z],\s*(?P<day>\w+),\s*(?P<time>[\d_]+ [AP]M)$",
        metadata_part
    )
    if virtual_comma_match:
        data = virtual_comma_match.groupdict()
        return {"class_info": {
            "region": clean_region(data["region"]),
            "location": None,
            "type": "Virtual",
            "day": data["day"],
            "time": data["time"],
            "facilitators": facilitators
        }}

    # Virtual format with "Virtual EC3" phrase (e.g., South America Virtual EC3, V, ...)
    virtual_phrase_match = re.match(
        r"^(?P<region>.+?)\s+Virtual\s+EC3?,\s*[A-Z],\s*(?P<day>\w+),\s*(?P<time>[\d_]+ [AP]M)$",
        metadata_part
    )
    if virtual_phrase_match:
        data = virtual_phrase_match.groupdict()
        return {"class_info": {
            "region": clean_region(data["region"]),
            "location": None,
            "type": "Virtual",
            "day": data["day"],
            "time": data["time"],
            "facilitators": facilitators
        }}

    raise ValueError(f"Unrecognized filename format: {file_name}")
