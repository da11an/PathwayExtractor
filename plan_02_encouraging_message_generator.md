# Plan 02: Auto-Generate Encouraging Messages for Students

## Goal

Create a new module that generates personalized, encouraging messages (1-2 sentences) for each student based on their learning data. Messages should:

- Be responsive to the student's specific learning context
- Always be positive and encouraging
- Have enough variety to not appear obviously computer-generated
- Celebrate achievements and encourage continued progress

## Available Student Data

From `class_student_records`, each student has:

```python
{
    "weekly_submissions": {
        "week_1": 5,
        "week_2": 8,
        "week_3": 12,
        # ... up to current week
    },
    "submissions_by_skill": {
        "grammar": 10,
        "reading": 8,
        "writing": 5,
        "speaking": 3,
        "listening": 7,
        "vocabulary": 6
    },
    "skill_scores": {
        "grammar": 3,
        "reading": 2,
        "writing": 1,
        # ... levels achieved per skill
    }
}
```

## Pattern Detection Categories

### 1. Weekly Progress Patterns
- **Improving**: Recent weeks show upward trend
- **Consistent**: Steady effort across weeks
- **Strong finish**: Last week was their best
- **Building momentum**: Last 2-3 weeks show acceleration
- **Just started**: Only 1-2 weeks of data
- **Comeback**: Low period followed by recovery

### 2. Achievement Patterns
- **High performer**: Total units above threshold (e.g., 50+)
- **Milestone reached**: Hit specific unit counts (10, 25, 50, 100)
- **Skill mastery**: High level in a specific skill
- **Well-rounded**: Good progress across all skills
- **Specialist**: Exceptional in one skill area

### 3. Effort Patterns
- **Active this week**: Recent submission activity
- **Consistent worker**: No zero weeks
- **Strong average**: Above-average weekly units

## Message Template System

### Structure
Each message will be composed of:
1. **Opening**: Personalized greeting element (optional, brief)
2. **Core message**: The main encouraging statement based on detected pattern
3. **Closing**: Forward-looking encouragement (optional)

### Template Variety Strategy
To avoid repetition:
- Multiple templates per pattern (5-10 variations each)
- Randomized selection with seed based on student name (consistent per student)
- Dynamic word substitutions (synonyms, phrasings)
- Combine patterns when multiple apply

### Example Templates by Pattern

**Improving Trend:**
- "Your progress over the past few weeks shows real dedication—keep building on that momentum!"
- "Each week you're getting stronger. Your growth is inspiring!"
- "Your upward trend shows what consistent effort can achieve."

**Best Week:**
- "This was your strongest week yet—outstanding work!"
- "You set a new personal best this week. Celebrate that achievement!"
- "What a week! You've outdone yourself."

**Consistent Effort:**
- "Your steady commitment week after week is truly admirable."
- "Consistency is the key to mastery, and you're proving it."
- "Your reliable effort every week is building something great."

**High Performer:**
- "With {total} units completed, you're making exceptional progress!"
- "Your dedication has resulted in {total} units—that's remarkable."

**Skill Strength:**
- "Your {skill} skills are really shining through!"
- "You're developing strong {skill} abilities—keep it up!"

**Just Getting Started:**
- "You're off to a great start! Every expert was once a beginner."
- "Your first steps are the most important—and you're taking them!"

## Architecture

### New Module: `pathway_extractor/message_generator.py`

```python
# Core functions:

def analyze_student_progress(student_data: dict) -> dict:
    """Analyze student data and return detected patterns with scores."""
    
def select_message_template(patterns: dict, student_name: str) -> str:
    """Select appropriate template based on patterns, using student name as seed."""
    
def generate_encouraging_message(student_name: str, student_data: dict) -> str:
    """Main function: Generate a personalized encouraging message."""
    
def fill_template(template: str, context: dict) -> str:
    """Fill in template variables with actual values."""
```

### Message Templates Storage

Templates stored as module-level constants organized by pattern:

```python
TEMPLATES = {
    "improving": [
        "Your progress over the past few weeks shows real dedication!",
        "Each week you're getting stronger—keep it up!",
        # ... more variations
    ],
    "best_week": [...],
    "consistent": [...],
    "high_performer": [...],
    # ... etc
}

CLOSINGS = [
    "Keep going!",
    "You've got this!",
    "The best is yet to come!",
    # ... etc
]
```

## Integration Points

### 1. Update `generate_messages.py`
- Import `generate_encouraging_message` from new module
- Call it for each student when generating HTML
- Replace or augment the static greeting message

### 2. Update `generate_progress_report_html()`
- Add `encouraging_message` parameter
- Display the personalized message in the HTML output

## Implementation Steps

- [x] Step 1: Create `message_generator.py` with pattern detection functions
- [x] Step 2: Create template library with 5-10 variations per pattern
- [x] Step 3: Implement message selection logic with variety mechanisms
- [x] Step 4: Add template filling with dynamic values
- [x] Step 5: Integrate with `generate_messages.py`
- [x] Step 6: Test with sample data to verify variety and appropriateness

## Implementation Notes

### Pattern Detection (12 patterns implemented)
1. `just_started` - Only 1-2 weeks of data
2. `improving` - Recent weeks trending upward
3. `best_week` - Current week is personal best
4. `building_momentum` - Last 2-3 weeks accelerating (50%+ increase)
5. `consistent` - Low variance, steady effort
6. `no_zero_weeks` - Activity every single week
7. `comeback` - Low start followed by recovery
8. `high_performer` - 50+ or 100+ total units
9. `milestone` - Hit 10, 25, 50, 75, or 100 units
10. `strong_average` - 5+ or 8+ units per week
11. `skill_strength` - One skill notably higher than others
12. `well_rounded` - Good progress across all skills

### Variety Mechanisms
- MD5 hash of student name used as seed for deterministic selection
- 5-10 template variations per pattern
- Optional closing phrases (weighted toward no closing for brevity)
- Up to 2 patterns combined per message

### Test Results
Messages show good variety across different students with same data:
- "You've topped your own record this week—well done!"
- "A new personal record! Your hard work is paying off."
- "You set a new personal best this week—celebrate that achievement!"
- Different closings: "The best is yet to come!", "Keep going!", or none

## Design Principles

1. **Always Positive**: Never mention negatives, gaps, or failures
2. **Specific but Not Robotic**: Reference actual data but in natural language
3. **Variety**: Same student gets same message (deterministic), but different students get different messages
4. **Appropriate Length**: 1-2 sentences, readable at a glance
5. **Culturally Sensitive**: Language appropriate for international, faith-based context
6. **No Comparisons**: Never compare students to each other

## Example Output

**Student A** (improving trend, 45 total units):
> "Your progress over the past few weeks shows real dedication! With 45 units completed, you're building something great."

**Student B** (best week ever, strong in grammar):
> "This was your strongest week yet—outstanding work! Your grammar skills are really shining."

**Student C** (just started, 2 weeks):
> "You're off to a great start! Every expert was once a beginner, and you're taking those important first steps."

**Student D** (consistent, well-rounded):
> "Your steady commitment week after week is truly admirable. Keep building on that solid foundation!"

## Files to Create/Modify

| File | Action |
|------|--------|
| `pathway_extractor/message_generator.py` | **CREATE** - New module |
| `pathway_extractor/generate_messages.py` | **MODIFY** - Integrate new messages |

## Success Criteria

1. Messages feel personal and specific to each student
2. No two students in a class get identical messages (unless data is identical)
3. Messages are always positive and encouraging
4. Language is natural, not obviously templated
5. Messages integrate smoothly into existing HTML output
