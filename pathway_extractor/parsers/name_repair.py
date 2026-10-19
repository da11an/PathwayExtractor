"""Conservative, opt-in repair using independent full-name evidence in the PDF."""
import re


def normalize_name(value):
    return " ".join(str(value).casefold().split())


def reference_names(reference_lines):
    """Read whole text runs, separated by numeric cells in side-by-side tables.

    pdfplumber may return 'Active Student 17 17 Inactive Student' on one line.
    Numbers delimit independent name runs; we never use arbitrary substring or
    fuzzy matches, nor join text across lines or numeric cells.
    """
    names = set()
    for line in reference_lines:
        run = []
        for token in (line or "").split() + ["0"]:
            if re.fullmatch(r"[+-]?\d+(?:\.\d+)?", token):
                name = " ".join(run)
                if name and re.fullmatch(r"[\w\s.'’\-]+", name) and not any(c.isdigit() for c in name):
                    names.add(normalize_name(name))
                run = []
            else:
                run.append(token)
    return names


def repair_supported_names(table, known_names, reference_lines):
    """Join adjacent name fragments only when an independent PDF line confirms them.

    The no-submissions roster can contain students missing from the weekly table.
    Exact line evidence avoids guessing from name length or treating every empty
    row as a continuation. Explicit zeros/placeholders are data, not empty cells.
    Existing complete names are protected, and ambiguous multi-line matches are
    left alone. Inputs and numeric cells are never modified.
    """
    evidence = reference_names(reference_lines)
    complete = evidence | {normalize_name(name) for name in known_names}

    def blank(value):
        return value is None or (isinstance(value, str) and not value.strip())

    # Match the existing merger's treatment of actual blank extraction gaps,
    # but retain rows containing numeric zeros or placeholders.
    rows = [list(row) for row in table if row and not all(blank(v) for v in row)]
    result = []
    i = 0
    while i < len(rows):
        first = rows[i]
        name = str(first[0] or "").strip()
        # Only extend a row that actually carries data; never borrow a neighbor's
        # values or merge a complete student (including a zero-activity student).
        if not name or normalize_name(name) in complete or not any(not blank(v) for v in first[1:]):
            result.append(first)
            i += 1
            continue
        candidates = []
        combined = name
        for j in range(i + 1, len(rows)):
            continuation = rows[j]
            fragment = str(continuation[0] or "").strip()
            if (not fragment or len(continuation) != len(first)
                    or any(not blank(v) for v in continuation[1:])
                    or normalize_name(fragment) in complete):
                break
            combined += " " + fragment
            if normalize_name(combined) in evidence:
                candidates.append((j, combined))
        if len(candidates) == 1:
            end, full_name = candidates[0]
            result.append([full_name] + first[1:])
            i = end + 1
        else:
            result.append(first)
            i += 1
    return result
