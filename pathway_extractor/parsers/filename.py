import os
import re

def parse_filename(file_name: str) -> dict:
    base = os.path.splitext(file_name)[0].strip()

    # Handle underscore-based format without " - " separator
    # e.g. "Utah_EC3,_V,_Thursday,_10_00_AM_Prince_20260204_142732"
    # e.g. "Utah_EC3_-_St_George_449_S_300_E_St._George_Utah,_IP,_Wednesday,_07_00_PM_Stillman-Stillman_20260206_174121659"
    if " - " not in base and "_" in base:
        # Strip timestamp suffix (YYYYMMDD_HHMMSS or YYYYMMDD_HHMMSSSSS)
        # Handle both 6-digit (seconds) and 9-digit (milliseconds) timestamps
        ts_match = re.search(r'_(\d{8}_\d{6,9})$', base)
        if ts_match:
            base_no_ts = base[:ts_match.start()]
            # Find AM/PM marker to split metadata from facilitator
            ampm_match = re.search(r'_([AP]M)_', base_no_ts)
            if ampm_match:
                metadata_underscored = base_no_ts[:ampm_match.end() - 1]  # up to and including AM/PM
                facilitator = base_no_ts[ampm_match.end():]  # after AM/PM_
                # Replace underscores with spaces, but preserve underscores between digits (time format)
                metadata_part = metadata_underscored.replace(',_', ', ')
                metadata_part = re.sub(r'(?<!\d)_|_(?!\d)', ' ', metadata_part)
                facilitators_part = facilitator.replace('_', ' ')
                # Reconstruct as normalized format and re-enter
                base = f"{metadata_part} - {facilitators_part}"

    if " - " not in base:
        raise ValueError(f"Missing ' - ' in filename: {file_name}")

    metadata_part, facilitators_part = base.rsplit(" - ", 1)
    facilitators = [f.strip() for f in facilitators_part.split(",") if f.strip()]

    def clean_region(region):
        region = region.replace("Virtual", "").strip()
        region = region.replace("AW - GHANA", "Africa West - Ghana")
        region = region.replace("AW - COTE D'IVOIRE", "Africa West - Cote d'Ivoire")
        region = region.replace("AW - LIBERIA", "Africa West - Liberia")
        region = region.replace("AW - SIERRA LEONE", "Africa West - Sierra Leone")
        region = region.replace("EnglishConnect 3", "").strip()
        region = region.replace("English Connect 3", "").strip()
        region = region.replace("EC3", "").strip()
        region = region.replace("EC 3", "").strip()
        region = region.replace("ENGLISHCONNECT", "").strip()
        region = region.rstrip(" -")
        return region

    # In-person format with location that may include commas
    # Time can have underscores, hyphens, colons, or spaces: 10_00 AM, 10-00 AM, 10:00 AM, 07 00 PM
    in_person_match = re.match(
        r"^(?P<region>.+?)\s+EC3?\s*-\s*(?P<location>.+?),\s*(?P<type>IP|In\s?Person),\s*(?P<day>\w+),\s*(?P<time>[\d_\-:\s]+ [AP]M)$",
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
    # Time can have underscores, hyphens, colons, or spaces: 10_00 AM, 10-00 AM, 10:00 AM, 07 00 PM
    virtual_comma_match = re.match(
        r"^(?P<region>.+?)\s+EC3?,\s*[A-Z],\s*(?P<day>\w+),\s*(?P<time>[\d_\-:\s]+ [AP]M)$",
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
    # Time can have underscores, hyphens, colons, or spaces: 10_00 AM, 10-00 AM, 10:00 AM, 07 00 PM
    virtual_phrase_match = re.match(
        r"^(?P<region>.+?)\s+Virtual\s+EC3?,\s*[A-Z],\s*(?P<day>\w+),\s*(?P<time>[\d_\-:\s]+ [AP]M)$",
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

    # Generic Virtual fallback (e.g., "Brazil Virtual EnglishConnect 3, V, Wednesday, 08_00 PM")
    # Time can have underscores, hyphens, colons, or spaces: 10_00 AM, 10-00 AM, 10:00 AM, 07 00 PM
    generic_virtual_match = re.match(
        r"^(?P<region>.+?),\s*V,\s*(?P<day>\w+),\s*(?P<time>[\d_\-:\s]+ [AP]M)$",
        metadata_part
    )
    if generic_virtual_match:
        data = generic_virtual_match.groupdict()
        return {"class_info": {
            "region": clean_region(data["region"]),
            "location": None,
            "type": "Virtual",
            "day": data["day"],
            "time": data["time"],
            "facilitators": facilitators
        }}

    # Generic In Person fallback (e.g., "Alicia Philippines Stake, IP, Wednesday, 08_30 PM")
    # Time can have underscores, hyphens, colons, or spaces: 10_00 AM, 10-00 AM, 10:00 AM, 07 00 PM
    generic_ip_match = re.match(
        r"^(?P<region>.+?),\s*(IP|In\s?Person),\s*(?P<day>\w+),\s*(?P<time>[\d_\-:\s]+ [AP]M)$",
        metadata_part
    )
    if generic_ip_match:
        data = generic_ip_match.groupdict()
        return {"class_info": {
            "region": clean_region(data["region"]),
            "location": None,
            "type": "In Person",
            "day": data["day"],
            "time": data["time"],
            "facilitators": facilitators
        }}

    raise ValueError(f"Unrecognized filename format: {file_name}")
