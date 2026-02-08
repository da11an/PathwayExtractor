"""
Encouraging Message Generator for Students

Generates personalized, positive messages based on student learning data.
Messages are 1-2 sentences, responsive to learning context, and varied
to avoid appearing obviously computer-generated.
"""

import hashlib
from typing import Dict, List, Optional, Tuple


# =============================================================================
# MESSAGE TEMPLATES
# =============================================================================

# Templates organized by pattern type
# Each pattern has multiple variations for variety

TEMPLATES = {
    # Weekly Progress Patterns
    "improving": [
        "Your progress over the past few weeks shows real dedication!",
        "Each week you're getting stronger—your growth is inspiring!",
        "Your upward trend shows what consistent effort can achieve.",
        "You're building momentum with each passing week!",
        "Your recent progress is truly impressive—keep climbing!",
        "Week by week, you're proving what's possible with dedication.",
        "Your improvement curve is heading in a wonderful direction!",
        "The progress you've made recently is something to be proud of.",
    ],
    
    "best_week": [
        "This was your strongest week yet—outstanding work!",
        "You set a new personal best this week—celebrate that achievement!",
        "What a week! You've outdone yourself.",
        "Your best week so far shows what you're truly capable of!",
        "A new personal record! Your hard work is paying off.",
        "This week you reached new heights—amazing effort!",
        "You've topped your own record this week—well done!",
    ],
    
    "consistent": [
        "Your steady commitment week after week is truly admirable.",
        "Consistency is the key to mastery, and you're proving it.",
        "Your reliable effort every week is building something great.",
        "Week after week, you show up and put in the work—that's inspiring.",
        "Your consistent dedication is the foundation of real progress.",
        "Steady and strong—your consistent effort is making a difference.",
        "Your dependable work ethic is setting you up for success.",
    ],
    
    "building_momentum": [
        "You're really picking up steam—keep that momentum going!",
        "Your recent acceleration is exciting to see!",
        "You're hitting your stride now—great work!",
        "The momentum you're building is powerful!",
        "Your pace is picking up beautifully—keep it going!",
    ],
    
    "just_started": [
        "You're off to a great start! Every expert was once a beginner.",
        "Your first steps are the most important—and you're taking them!",
        "Welcome to the journey! You've already begun something meaningful.",
        "Great beginnings lead to great achievements—you're on your way!",
        "Starting is often the hardest part, and you've done it!",
        "Every journey begins with a single step—you've taken yours!",
    ],
    
    "comeback": [
        "It's great to see you back in action!",
        "Your return to learning shows real determination.",
        "Welcome back! Your renewed effort is inspiring.",
        "You're back and making progress—that takes courage!",
    ],
    
    # Achievement Patterns
    "high_performer": [
        "With {total} units completed, you're making exceptional progress!",
        "Your dedication has resulted in {total} units—that's remarkable.",
        "{total} units completed shows incredible commitment!",
        "You've completed {total} units—your hard work is evident!",
        "With {total} units under your belt, you're achieving great things!",
    ],
    
    "milestone": [
        "Congratulations on reaching {milestone} units!",
        "You've hit the {milestone}-unit milestone—well done!",
        "{milestone} units completed is a wonderful achievement!",
        "Reaching {milestone} units is a testament to your effort!",
    ],
    
    "skill_strength": [
        "Your {skill} skills are really shining through!",
        "You're developing strong {skill} abilities—keep it up!",
        "Your {skill} work has been particularly impressive!",
        "You're showing real talent in {skill}!",
        "Your {skill} progress stands out—excellent work!",
    ],
    
    "well_rounded": [
        "You're making great progress across all skill areas!",
        "Your balanced approach to learning is paying off.",
        "Strong work across the board—you're developing well-rounded skills!",
        "You're building a solid foundation in every area!",
    ],
    
    # Effort Patterns
    "active_learner": [
        "Your active engagement with learning is wonderful to see!",
        "You're staying engaged and making it count!",
        "Your continued activity shows real dedication!",
    ],
    
    "no_zero_weeks": [
        "You've put in effort every single week—that's commitment!",
        "Not a single week without progress—impressive dedication!",
        "Your streak of consistent effort is truly remarkable!",
    ],
    
    "strong_average": [
        "Averaging {average:.1f} units per week shows excellent dedication!",
        "Your weekly average of {average:.1f} units reflects strong effort!",
        "With {average:.1f} units per week on average, you're doing great!",
    ],
    
    # Course Completion Patterns
    "pathway_ready": [
        "Congratulations! You've met all the requirements for Pathway Connect!",
        "You've done it! Your completion certificate is within reach!",
        "All your hard work has paid off—you're ready for Pathway Connect!",
        "What an achievement! You've completed the language requirements!",
        "You've reached the finish line—Pathway Connect awaits!",
    ],
    
    "near_completion": [
        "You're so close to completing the program—keep going!",
        "Just a little more and you'll have your completion certificate!",
        "The finish line is in sight—you're almost there!",
        "You're on the verge of a major achievement!",
        "With {certified_count} of 6 skills at target, you're nearly done!",
    ],
    
    "skill_certified": [
        "You've reached the target level in {skill}—outstanding!",
        "Your {skill} has hit the goal—one step closer to completion!",
        "{skill} mastered! Keep this momentum going!",
        "Another skill at target level—your {skill} is where it needs to be!",
    ],
    
    "multiple_certifications": [
        "With {certified_count} skills at target level, you're making excellent progress!",
        "You've got {certified_count} skills checked off—great work toward completion!",
        "{certified_count} down, {remaining_count} to go—you're doing wonderfully!",
    ],
    
    # Current Block Focus (weekly_submissions = this term only)
    "block_dedication": [
        "Your dedication this block has been impressive!",
        "This term you're showing what focused effort can achieve.",
        "Your work this block reflects real commitment to learning.",
        "This term's effort is building your skills beautifully.",
    ],
    
    "block_strong_finish": [
        "You're finishing this block strong!",
        "What a way to close out this term—excellent work!",
        "This block's final stretch shows your determination.",
    ],
    
    # All-Time Achievement Focus (submissions_by_skill = accumulated across terms)
    "lifetime_achievement": [
        "Across all your studies, you've built {total_alltime} units of learning!",
        "Your overall journey shows {total_alltime} units of dedicated progress.",
        "With {total_alltime} units completed in your journey, you've come so far!",
    ],
    
    # Fallback/General
    "general": [
        "Keep up the great work—every unit brings you closer to your goals!",
        "Your effort is making a difference—keep going!",
        "You're on a wonderful learning journey—stay the course!",
        "Every step forward counts, and you're taking them!",
        "Your commitment to learning is inspiring!",
        "You're doing meaningful work—be proud of your progress!",
        "Keep pressing forward—you're capable of great things!",
    ],
}

# Optional closing phrases (can be appended for variety)
CLOSINGS = [
    "Keep going!",
    "You've got this!",
    "The best is yet to come!",
    "Keep up the wonderful work!",
    "Onward and upward!",
    "Your future is bright!",
    "",  # Sometimes no closing is best
    "",
    "",  # Weight toward no closing to keep messages concise
]

# Skill name display mappings
SKILL_DISPLAY_NAMES = {
    "grammar": "grammar",
    "reading": "reading", 
    "writing": "writing",
    "speaking": "speaking",
    "listening": "listening",
    "vocabulary": "vocabulary",
}

# Certificate requirements: level needed for each skill
# Level 4 for grammar, vocabulary, reading, writing
# Level 3 for speaking, listening (level 4 exists but not required)
CERTIFICATE_REQUIREMENTS = {
    "grammar": 4,
    "vocabulary": 4,
    "reading": 4,
    "writing": 4,
    "speaking": 3,
    "listening": 3,
}


# =============================================================================
# PATTERN DETECTION
# =============================================================================

def analyze_student_progress(student_data: dict) -> Dict[str, any]:
    """
    Analyze student data and return detected patterns with scores.
    
    Data semantics:
    - weekly_submissions: Current block/term only (units this term by week)
    - submissions_by_skill: All-time accumulated (total units ever per skill)
    - skill_scores: All-time levels achieved (highest level per skill)
    
    Args:
        student_data: Dict with weekly_submissions, submissions_by_skill, skill_scores
        
    Returns:
        Dict with pattern names as keys and pattern info as values
    """
    patterns = {}
    
    # Extract weekly data (CURRENT BLOCK ONLY)
    weekly = student_data.get("weekly_submissions", {})
    weekly_values = []
    for key, value in sorted(weekly.items()):
        if key.startswith("week_"):
            try:
                weekly_values.append(int(value) if value else 0)
            except (ValueError, TypeError):
                weekly_values.append(0)
    
    # Extract skill data (ALL-TIME)
    skill_units = student_data.get("submissions_by_skill", {})  # All-time units per skill
    skill_scores = student_data.get("skill_scores", {})  # All-time levels
    
    # Calculate totals
    block_total = sum(weekly_values) if weekly_values else 0  # This block only
    num_weeks = len(weekly_values)
    average_per_week = block_total / num_weeks if num_weeks > 0 else 0
    
    # All-time total from skill units
    # Only sum known skill fields to avoid double-counting if a "Total" column exists
    # Headers are normalized: "vocab"->"vocabulary", "read"->"reading", "write"->"writing", 
    # "speak"->"speaking", "listen"->"listening", "Total"->"total"
    known_skill_fields = {"grammar", "vocabulary", "reading", "writing", "speaking", "listening"}
    alltime_total = sum(
        v for k, v in skill_units.items() 
        if k.lower() in known_skill_fields 
        and isinstance(v, (int, float)) 
        and v > 0
    )
    
    # === Certificate Completion Tracking ===
    # Check how many skills are at their required level
    certified_skills = []
    skills_at_target = 0
    
    for skill, required_level in CERTIFICATE_REQUIREMENTS.items():
        current_level = skill_scores.get(skill, -1)
        # Handle string levels like "-" or "-1"
        if isinstance(current_level, str):
            current_level = -1 if current_level in ["-", "-1", ""] else int(current_level) if current_level.lstrip('-').isdigit() else -1
        
        if current_level >= required_level:
            skills_at_target += 1
            certified_skills.append(skill)
    
    # Store context for template filling
    patterns["_context"] = {
        "total": block_total,  # Current block total (for weekly patterns)
        "total_alltime": alltime_total,  # All-time total
        "average": average_per_week,
        "num_weeks": num_weeks,
        "weekly_values": weekly_values,
        "certified_count": skills_at_target,
        "remaining_count": 6 - skills_at_target,
        "certified_skills": certified_skills,
    }
    
    # --- Pattern Detection ---
    
    # 1. Just started (1-2 weeks)
    if num_weeks <= 2:
        patterns["just_started"] = {"score": 10, "priority": 1}
    
    # 2. Check for improving trend (last 3 weeks trending up)
    if num_weeks >= 3:
        recent = weekly_values[-3:]
        if recent[0] < recent[1] < recent[2]:
            patterns["improving"] = {"score": 8, "priority": 2}
        elif num_weeks >= 2 and weekly_values[-2] < weekly_values[-1]:
            # At least last week was better than previous
            patterns["improving"] = {"score": 5, "priority": 3}
    
    # 3. Best week (current week is personal best)
    if num_weeks >= 2 and weekly_values:
        current_week = weekly_values[-1]
        previous_max = max(weekly_values[:-1]) if len(weekly_values) > 1 else 0
        if current_week > 0 and current_week > previous_max:
            patterns["best_week"] = {"score": 9, "priority": 1}
    
    # 4. Building momentum (last 2-3 weeks accelerating)
    if num_weeks >= 3:
        recent = weekly_values[-3:]
        # Each week significantly higher than last
        if all(recent[i] < recent[i+1] for i in range(len(recent)-1)):
            if recent[-1] >= recent[0] * 1.5:  # 50% increase over 3 weeks
                patterns["building_momentum"] = {"score": 7, "priority": 2}
    
    # 5. Consistent (low variance, no zeros)
    if num_weeks >= 3:
        non_zero_weeks = [v for v in weekly_values if v > 0]
        if len(non_zero_weeks) == num_weeks:  # No zero weeks
            patterns["no_zero_weeks"] = {"score": 6, "priority": 3}
            
            # Check for consistency (coefficient of variation < 0.5)
            if average_per_week > 0:
                variance = sum((v - average_per_week) ** 2 for v in weekly_values) / num_weeks
                std_dev = variance ** 0.5
                cv = std_dev / average_per_week
                if cv < 0.5:
                    patterns["consistent"] = {"score": 7, "priority": 2}
    
    # 6. Comeback (had zeros/low, now active)
    if num_weeks >= 4:
        first_half = weekly_values[:num_weeks//2]
        second_half = weekly_values[num_weeks//2:]
        first_avg = sum(first_half) / len(first_half) if first_half else 0
        second_avg = sum(second_half) / len(second_half) if second_half else 0
        if first_avg < 2 and second_avg >= 5:
            patterns["comeback"] = {"score": 6, "priority": 2}
    
    # 7. High performer (total units above thresholds)
    if block_total >= 100:
        patterns["high_performer"] = {"score": 9, "priority": 1}
    elif block_total >= 50:
        patterns["high_performer"] = {"score": 7, "priority": 2}
    
    # 8. Milestone reached
    milestones = [100, 75, 50, 25, 10]
    for m in milestones:
        if block_total >= m:
            patterns["_context"]["milestone"] = m
            if m >= 50:
                patterns["milestone"] = {"score": 6, "priority": 3}
            break
    
    # 9. Strong average (above 5 units/week)
    if average_per_week >= 8:
        patterns["strong_average"] = {"score": 7, "priority": 2}
    elif average_per_week >= 5:
        patterns["strong_average"] = {"score": 5, "priority": 3}
    
    # 10. Skill strength (one skill notably higher)
    if skill_units:
        skill_values = [(k, v) for k, v in skill_units.items() 
                        if isinstance(v, (int, float)) and v > 0]
        if skill_values:
            skill_values.sort(key=lambda x: x[1], reverse=True)
            top_skill, top_value = skill_values[0]
            if len(skill_values) > 1:
                second_value = skill_values[1][1]
                # Top skill is 50% higher than second
                if top_value >= second_value * 1.5 and top_value >= 5:
                    patterns["skill_strength"] = {"score": 5, "priority": 3}
                    patterns["_context"]["skill"] = SKILL_DISPLAY_NAMES.get(
                        top_skill.lower(), top_skill
                    )
    
    # 11. Well-rounded (good progress across all skills)
    if skill_units:
        skill_values = [v for v in skill_units.values() 
                        if isinstance(v, (int, float))]
        if len(skill_values) >= 4:
            min_skill = min(skill_values)
            if min_skill >= 3:  # At least 3 units in every skill
                patterns["well_rounded"] = {"score": 5, "priority": 3}
    
    # 12. Active learner (has recent activity)
    if weekly_values and weekly_values[-1] > 0:
        patterns["active_learner"] = {"score": 3, "priority": 4}
    
    # === CERTIFICATE COMPLETION PATTERNS ===
    
    # 13. Pathway Ready (all 6 skills at target level)
    if skills_at_target == 6:
        patterns["pathway_ready"] = {"score": 15, "priority": 0}  # Highest priority!
    
    # 14. Near Completion (5 of 6 skills at target)
    elif skills_at_target == 5:
        patterns["near_completion"] = {"score": 12, "priority": 1}
    
    # 15. Multiple Certifications (2-4 skills at target)
    elif skills_at_target >= 2:
        patterns["multiple_certifications"] = {"score": 8, "priority": 2}
    
    # 16. Skill Certified (at least one skill at target, pick the first one for message)
    if certified_skills:
        patterns["_context"]["skill"] = SKILL_DISPLAY_NAMES.get(
            certified_skills[0].lower(), certified_skills[0]
        )
        if skills_at_target == 1:
            patterns["skill_certified"] = {"score": 6, "priority": 3}
    
    # === BLOCK/TERM FOCUS PATTERNS ===
    
    # 17. Block dedication (strong performance this block)
    if num_weeks >= 3 and average_per_week >= 6:
        patterns["block_dedication"] = {"score": 5, "priority": 3}
    
    # 18. Block strong finish (last 2 weeks are best of block)
    if num_weeks >= 4:
        last_two_avg = sum(weekly_values[-2:]) / 2
        first_weeks_avg = sum(weekly_values[:-2]) / (num_weeks - 2) if num_weeks > 2 else 0
        if last_two_avg > first_weeks_avg * 1.3:  # 30% better finish
            patterns["block_strong_finish"] = {"score": 6, "priority": 3}
    
    # 19. Lifetime achievement (significant all-time units)
    if alltime_total >= 100:
        patterns["lifetime_achievement"] = {"score": 7, "priority": 2}
    
    return patterns


# =============================================================================
# MESSAGE SELECTION AND GENERATION
# =============================================================================

def get_deterministic_index(seed_string: str, list_length: int) -> int:
    """
    Get a deterministic index based on a seed string.
    Same seed always produces same index.
    
    Args:
        seed_string: String to use as seed (e.g., student name)
        list_length: Length of list to index into
        
    Returns:
        Integer index in range [0, list_length)
    """
    if list_length <= 0:
        return 0
    hash_value = int(hashlib.md5(seed_string.encode()).hexdigest(), 16)
    return hash_value % list_length


def select_patterns_for_message(patterns: Dict[str, any], max_patterns: int = 2) -> List[str]:
    """
    Select the best patterns to use for the message.
    
    Args:
        patterns: Dict of detected patterns with scores
        max_patterns: Maximum number of patterns to combine
        
    Returns:
        List of pattern names to use
    """
    # Filter out context and get scorable patterns
    scorable = [
        (name, info) for name, info in patterns.items() 
        if not name.startswith("_") and isinstance(info, dict) and "score" in info
    ]
    
    if not scorable:
        return ["general"]
    
    # Sort by priority (lower = higher priority), then by score (higher = better)
    scorable.sort(key=lambda x: (x[1].get("priority", 5), -x[1].get("score", 0)))
    
    # Take top patterns
    selected = [name for name, _ in scorable[:max_patterns]]
    
    return selected if selected else ["general"]


def fill_template(template: str, context: dict) -> str:
    """
    Fill template variables with actual values.
    
    Args:
        template: Template string with {variable} placeholders
        context: Dict of variable values
        
    Returns:
        Filled template string
    """
    try:
        return template.format(**context)
    except KeyError:
        # If a variable is missing, return template without that substitution
        return template


def generate_encouraging_message(student_name: str, student_data: dict) -> str:
    """
    Generate a personalized encouraging message for a student.
    
    Args:
        student_name: Student's name (used for personalization and determinism)
        student_data: Dict with weekly_submissions, submissions_by_skill, skill_scores
        
    Returns:
        Encouraging message string (1-2 sentences)
    """
    # Analyze student progress
    patterns = analyze_student_progress(student_data)
    context = patterns.get("_context", {})
    
    # Select patterns to use
    selected_patterns = select_patterns_for_message(patterns)
    
    # Build message from selected patterns
    message_parts = []
    
    for i, pattern_name in enumerate(selected_patterns):
        templates = TEMPLATES.get(pattern_name, TEMPLATES["general"])
        
        # Use student name + pattern index as seed for deterministic selection
        seed = f"{student_name}_{pattern_name}_{i}"
        template_idx = get_deterministic_index(seed, len(templates))
        template = templates[template_idx]
        
        # Fill template with context
        filled = fill_template(template, context)
        message_parts.append(filled)
    
    # Combine parts
    message = " ".join(message_parts)
    
    # Optionally add a closing (deterministic based on name)
    closing_idx = get_deterministic_index(f"{student_name}_closing", len(CLOSINGS))
    closing = CLOSINGS[closing_idx]
    if closing:
        message = f"{message} {closing}"
    
    return message


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def generate_message_for_student(student_name: str, weekly_submissions: dict,
                                  submissions_by_skill: dict = None,
                                  skill_scores: dict = None) -> str:
    """
    Convenience function to generate message from individual data components.
    
    Args:
        student_name: Student's name
        weekly_submissions: Dict like {"week_1": 5, "week_2": 8, ...}
        submissions_by_skill: Optional dict of skill units
        skill_scores: Optional dict of skill levels
        
    Returns:
        Encouraging message string
    """
    student_data = {
        "weekly_submissions": weekly_submissions or {},
        "submissions_by_skill": submissions_by_skill or {},
        "skill_scores": skill_scores or {},
    }
    return generate_encouraging_message(student_name, student_data)


# =============================================================================
# TESTING / DEMO
# =============================================================================

if __name__ == "__main__":
    # Demo with sample data
    test_students = [
        {
            "name": "Maria Garcia",
            "data": {
                "weekly_submissions": {"week_1": 3, "week_2": 5, "week_3": 8, "week_4": 12},
                "submissions_by_skill": {"grammar": 10, "reading": 8, "writing": 5},
                "skill_scores": {"grammar": 3, "reading": 2},
            }
        },
        {
            "name": "John Smith",
            "data": {
                "weekly_submissions": {"week_1": 15, "week_2": 14, "week_3": 16, "week_4": 18},
                "submissions_by_skill": {"grammar": 15, "reading": 15, "writing": 15, "listening": 14, "vocabulary": 12},
                "skill_scores": {},
            }
        },
        {
            "name": "Sarah Johnson",
            "data": {
                "weekly_submissions": {"week_1": 5},
                "submissions_by_skill": {"grammar": 3, "reading": 2},
                "skill_scores": {},
            }
        },
        {
            "name": "David Chen",
            "data": {
                "weekly_submissions": {"week_1": 0, "week_2": 1, "week_3": 8, "week_4": 10},
                "submissions_by_skill": {"grammar": 8, "reading": 5, "writing": 3},
                "skill_scores": {},
            }
        },
        {
            "name": "Emma Wilson",
            "data": {
                "weekly_submissions": {"week_1": 10, "week_2": 12, "week_3": 11, "week_4": 10, "week_5": 13},
                "submissions_by_skill": {"grammar": 12, "reading": 10, "writing": 11, "speaking": 9, "listening": 10, "vocabulary": 8},
                "skill_scores": {},
            }
        },
    ]
    
    print("=" * 60)
    print("ENCOURAGING MESSAGE GENERATOR - DEMO")
    print("=" * 60)
    
    for student in test_students:
        name = student["name"]
        data = student["data"]
        
        # Analyze patterns
        patterns = analyze_student_progress(data)
        detected = [k for k in patterns.keys() if not k.startswith("_")]
        
        # Generate message
        message = generate_encouraging_message(name, data)
        
        print(f"\n📚 {name}")
        print(f"   Weekly: {list(data['weekly_submissions'].values())}")
        print(f"   Patterns: {', '.join(detected)}")
        print(f"   Message: \"{message}\"")
    
    print("\n" + "=" * 60)
    print("Testing determinism (same student = same message):")
    print("=" * 60)
    
    for _ in range(3):
        msg = generate_encouraging_message("Maria Garcia", test_students[0]["data"])
        print(f"   Maria Garcia: \"{msg}\"")
