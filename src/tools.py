from langchain_core.tools import tool

@tool
def tool_evaluate_candidate(candidate_name: str, skills_text: str) -> str:
    """Evaluates a candidate's skills (Python, C++, Web Development)."""
    required_skills = ["python", "c++", "web development"]
    skills_text_lower = skills_text.lower()
    
    match_count = sum(1 for skill in required_skills if skill in skills_text_lower)
    
    # Add decision logic!
    if match_count >= 2:
        return f"Result: {candidate_name} matches {match_count}/3 skills. STATUS: SHORTLISTED. Please ask the user if they want to schedule an interview."
    else:
        return f"Result: {candidate_name} matches {match_count}/3 skills. STATUS: REJECTED. Do not schedule."

@tool
def tool_schedule_interview(candidate_name: str, interview_date: str) -> str:
    """Schedules an interview. Input date as YYYY-MM-DD."""
    return f"SUCCESS: Interview for {candidate_name} scheduled for {interview_date}."

@tool
def tool_get_hr_policy(policy_topic: str) -> str:
    """Answers HR questions about 'leave', 'onboarding', or 'insurance'."""
    policies = {
        "leave": "20 days paid leave.",
        "onboarding": "Complete docs in 3 days.",
        "insurance": "Starts day 1."
    }
    return policies.get(policy_topic.lower(), "Topic not found.")