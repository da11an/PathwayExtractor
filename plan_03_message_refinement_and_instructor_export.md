# Plan 03: Message Refinement and Instructor Export

## Goals

1. **Refine message generation** to properly interpret the semantic meaning of data fields
2. **Add course completion tracking** to celebrate progress toward certification
3. **Create instructor export document** with all student messages for easy copy/paste

---

## Part 1: Data Field Semantics

### Current Understanding (Corrected)

| Field | Scope | Meaning |
|-------|-------|---------|
| `weekly_submissions` | **Current block/term only** | Units completed this term, by week |
| `submissions_by_skill` | **All-time accumulated** | Total units ever completed per skill |
| `skill_scores` | **All-time levels** | Highest level achieved per skill |

### Level System Details

**Level Values:**
- `-1` or `"-"` = Not yet evaluated
- `0` = Working in Level 1 but test not yet passed
- `1` = Level 1 completed (test passed)
- `2` = Level 2 completed
- `3` = Level 3 completed  
- `4` = Level 4 completed (highest)

**Skill-Specific Rules:**

| Skill | Level Advancement | Max Level | Required for Certificate |
|-------|-------------------|-----------|--------------------------|
| Grammar | Progressive difficulty (level = units completed) | 4 | Level 4 |
| Vocabulary | Progressive difficulty (level = units completed) | 4 | Level 4 |
| Reading | Complete units + pass test | 4 | Level 4 |
| Writing | Complete units + pass test | 4 | Level 4 |
| Speaking | Complete units + pass test | 4 | **Level 3** |
| Listening | Complete units + pass test | 4 | **Level 3** |

### Completion Certificate Requirements

A student earns a **completion certificate** when they achieve:
- Level 4 in: Grammar, Vocabulary, Reading, Writing
- Level 3 in: Speaking, Listening (can continue to level 4, but not required)

This certificate **satisfies the language entrance requirement** for Pathway Connect where they can take college courses.

---

## Part 2: Message Generation Refinements

### 2.1 Semantic Improvements

**Current Block Focus (weekly_submissions):**
- Use for: "this term", "this block", "recent weeks"
- Patterns: improving, best_week, consistent, building_momentum

**All-Time Achievement Focus (submissions_by_skill, skill_scores):**
- Use for: "overall progress", "total achievement", "your journey"
- Patterns: high_performer, milestone, skill_strength, well_rounded

### 2.2 New Patterns to Add

**Course Completion Progress:**
- `near_completion` - Close to certificate (5 of 6 skills at target)
- `skill_certified` - Reached max level in a skill
- `multiple_certifications` - 2+ skills at max level
- `pathway_ready` - All requirements met for Pathway Connect

**Level Progress:**
- `level_up_potential` - Close to passing a test (level 0 with high units)
- `first_level_achieved` - Recently got first level 1

### 2.3 Template Updates

**New templates for course completion:**
```
"You're making excellent progress toward your completion certificate!"
"With {certified_count} skills at their target level, you're well on your way!"
"Your {skill} has reached the highest level—outstanding achievement!"
"You're so close to qualifying for Pathway Connect—keep going!"
"Congratulations on reaching the requirements for Pathway Connect!"
```

**Refined templates distinguishing current vs all-time:**
```
# Current block focus
"This block you're showing real dedication with your consistent effort!"
"Your work this term demonstrates strong commitment."

# All-time achievement focus  
"Your overall journey shows {total} units of dedicated learning!"
"Across all your studies, you've built impressive skills."
```

---

## Part 3: Instructor Export Document

### 3.1 Key Design Decisions

1. **Messages in HTML only, NOT in PNG images**
   - PNG images remain data-focused (tables, stats)
   - Encouraging messages are ONLY in the standalone HTML document
   - This gives instructors control over personalization

2. **One HTML document per class folder**
   - Each class folder gets one `encouragement_messages.html` file
   - Contains messages for ALL students in that class
   - Instructors can open and copy/paste as needed

### 3.2 Format: HTML

HTML chosen for:
- Better formatting and readability
- Support for tasteful emoji use
- Easy copy/paste from browser
- Can be opened in any web browser

### 3.3 Document Structure

```html
<html>
<head>
    <title>Student Encouragement Messages - [Facilitator] [Day] [Time]</title>
    <style>
        /* Clean, printable styling */
    </style>
</head>
<body>
    <h1>📚 Student Encouragement Messages</h1>
    <p class="meta">Class: [Facilitator] - [Day] [Time] | Generated: [Date]</p>
    
    <div class="student-card">
        <h3>👤 Student Name</h3>
        <p class="message">💬 "Encouraging message here..."</p>
        <div class="stats">
            <span>This Block: X units</span>
            <span>All-Time: Y units</span>
            <span>Completion: X/6 skills</span>
        </div>
    </div>
    
    <!-- Repeat for each student in this class -->
</body>
</html>
```

**File Location:**
```
output/
└── [Region]_[Type]/
    └── [Facilitator]_[Day]_[Time]/
        ├── Student1.png           # Data only, no message
        ├── Student2.png           # Data only, no message
        └── encouragement_messages.html  # All messages for this class
```

### 3.4 Emoji Usage (Sparse)

| Context | Emoji | Usage |
|---------|-------|-------|
| Student name header | 👤 | Once per student |
| Message quote | 💬 | Once per message |
| High achievement | ⭐ | Only for near-completion or certified |
| Pathway ready | 🎓 | Only when all requirements met |

### 3.5 Integration

New function in `generate_messages.py`:
```python
def generate_class_encouragement_html(students: dict, class_info: dict, output_dir: Path) -> Path:
    """
    Generate HTML document with encouragement messages for all students in a class.
    
    Args:
        students: Dict of student_name -> student_data
        class_info: Class metadata (facilitators, day, time, region, etc.)
        output_dir: The class folder where PNG files are saved
    
    Returns:
        Path to generated encouragement_messages.html file
    """
```

Called from `generate_message()` after processing all students in a class.

### 3.6 Changes to PNG Generation

**Remove message from PNG:**
- `generate_progress_report_html()` will NO LONGER include the encouraging message
- PNG remains purely data-focused (tables showing units and levels)
- The static greeting "Hi, [Name]!" can remain, but personalized encouragement moves to HTML

---

## Implementation Steps

### Phase 1: Message Refinement
- [x] Step 1: Update `analyze_student_progress()` to track course completion metrics
- [x] Step 2: Add new patterns for certification progress (near_completion, pathway_ready, etc.)
- [x] Step 3: Add templates that distinguish current-block vs all-time achievements
- [x] Step 4: Refine existing templates for semantic accuracy

### Phase 2: PNG Cleanup
- [x] Step 5: Remove encouraging message from `generate_progress_report_html()`
- [x] Step 6: Keep static greeting but remove dynamic personalized message

### Phase 3: Instructor Export
- [x] Step 7: Create `generate_class_encouragement_html()` function
- [x] Step 8: Design HTML template with clean styling and sparse emoji
- [x] Step 9: Integrate into `generate_message()` to create one HTML per class folder
- [x] Step 10: Ensure HTML file is saved alongside student PNGs in class folder

### Phase 4: Testing
- [x] Step 11: Test with sample data across different progress levels
- [x] Step 12: Verify instructor HTML renders correctly in browser
- [x] Step 13: Verify PNG images no longer contain encouraging messages

## Implementation Complete ✅

### New Patterns Added:
- `pathway_ready` - All 6 skills at target (highest priority)
- `near_completion` - 5 of 6 skills at target
- `multiple_certifications` - 2+ skills at target
- `skill_certified` - 1 skill at target
- `block_dedication` - Strong performance this term
- `block_strong_finish` - Finishing term strong
- `lifetime_achievement` - 100+ all-time units

### Test Results:
- Maria Garcia (5/6 skills): "You're so close to completing the program—keep going!"
- John Smith (6/6 skills): "You've done it! Your completion certificate is within reach!"
- Sarah Johnson (new): "Great beginnings lead to great achievements—you're on your way!"
- David Chen (comeback): "This week you reached new heights—amazing effort!"

---

## Files to Modify

| File | Changes |
|------|---------|
| `pathway_extractor/message_generator.py` | Add completion tracking, new patterns, refined templates |
| `pathway_extractor/generate_messages.py` | Remove message from PNG, add `generate_class_encouragement_html()` |
| `pathway_extractor/main.py` | No changes needed (generate_message already handles class-level processing) |

---

## Success Criteria

1. Messages properly reflect current-block vs all-time achievements
2. Students near completion get appropriate encouragement about Pathway Connect
3. **PNG images contain data only** (no encouraging messages)
4. **One HTML file per class folder** with all student messages
5. Instructor HTML document is clean and easy to use for copy/paste
6. Emoji usage is tasteful and sparse (not overwhelming)
7. Copy/paste from HTML preserves message text cleanly
