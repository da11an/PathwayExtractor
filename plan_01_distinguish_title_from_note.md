# Plan 01: Distinguish Table Title from Explanatory Note

## Problem

On page2_text, there are two instances of the title text "Assignments Submitted by Week":
1. **Table Title (Left)**: `*Assignments Submitted by Week` - the actual header of the table, in a larger/bold font
2. **Explanatory Note (Right)**: `*Assignments Submitted by Week: This includes learner submissions...` - smaller body text in the margin

The current detection logic sometimes picks the explanatory note (which appears higher on the page in some PDF versions) instead of the actual table title.

## Proposed Solutions

### Option A: Proximity to Column Header
1. Find ALL instances of the title text on the page
2. Find ALL instances of the expected first column header text (e.g., "EC3EnrollmentStatus", "pw_contactname")
3. For each title instance, calculate distance to nearest column header
4. The title with the closest column header below it is the actual table title

**Pros**: Directly validates that a table exists below the title
**Cons**: Depends on successfully finding column headers; adds complexity

### Option B: Font Size Detection (Recommended)
1. Find ALL instances of the title text on the page
2. For each instance, get the font size from character-level data (`page.chars`)
3. The title instance with the **largest font size** is the actual table title

**Pros**: 
- Simple and direct - table titles are typically styled larger
- Independent of column header detection
- More robust to layout variations
- pdfplumber provides char-level font info via `page.chars`

**Cons**: Requires accessing character-level data (slightly more complex API)

## Recommendation

**Option B (Font Size Detection)** is recommended because:
- Table titles are inherently styled with larger fonts for visual hierarchy
- It's a single criterion that directly reflects the design intent
- It doesn't add dependencies on other detection steps
- pdfplumber's `page.chars` provides `size` attribute for each character

## Implementation Plan

### Step 1: Create helper function to get font size for text at position
- Access `page.chars` to get character-level data
- Filter chars that fall within the bounding box of a found text line
- Return the average or dominant font size

### Step 2: Modify `find_title_text()` to find ALL matches
- Instead of returning the first/best match, return a list of all matches
- Each match includes position info AND font size

### Step 3: Create `find_best_title_match()` function
- Takes the list of all title matches
- Returns the match with the largest font size
- Falls back to topmost match if font sizes are equal

### Step 4: Update `analyze_pdf_for_tables()` to use the new logic
- Call the new multi-match finder
- Select the best match based on font size
- Continue with existing table detection from there

## Files to Modify

- `pathway_extractor/config_generator.py`:
  - Add `get_font_size_at_position()` helper
  - Modify `find_title_text()` to return all matches with font info
  - Add `find_best_title_match()` selector function
  - Update `analyze_pdf_for_tables()` to use new selection logic

## Testing

1. Run the extractor on PDFs from `OneDrive_1_1-22-2026/` where the bug was observed
2. Verify debug output shows the correct table title is selected
3. Verify the table bounds are correctly centered on the actual table

## Status

- [x] Step 1: Create font size helper (`get_font_size_at_position()`)
- [x] Step 2: Create find_all_title_matches to find all matches with font info
- [x] Step 3: Create find_best_title_match selector (selects by largest font)
- [x] Step 4: Update analyze_pdf_for_tables to use new selection logic
- [x] Testing - Verified fix on OneDrive_1_1-22-2026.zip

## Results

**Before the fix:**
- Title captured entire line: `*Assignments Submitted by Week *Learners with No Submissions`
- Wrong center position: x_center=810.3 (center of whole line)
- Wrong width: 1109.6 points

**After the fix:**
- Title correctly extracted: `*Assignments Submitted by Week` (just target phrase)
- Correct center position: x_center=439.4 (center of actual title)
- Correct width: 367.8 points

**Font size detection worked correctly:**
- Found 2 instances on page
- Instance 1: font_size=20.0 (explanatory note in body text)
- Instance 2: font_size=24.0 (actual table title in header)
- Correctly selected the larger font (24.0) as the table title
