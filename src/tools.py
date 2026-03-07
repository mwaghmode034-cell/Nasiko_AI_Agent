import os
from langchain.tools import tool

# --- Prompt_Mavaale Mock Databases ---
BOOKED_SLOTS = ["March 12", "March 15"]
ONBOARDING_DB = {
    "Aditya": {"docs_submitted": False, "background_check": "Pending", "laptop_assigned": False},
    "Sundram": {"docs_submitted": True, "background_check": "Completed", "laptop_assigned": True}
}

@tool
def tool_evaluate_candidate(candidate_name: str, skills_text: str) -> str:
    """Evaluates a candidate based on weighted technical scoring (Python, C++, Web Dev)."""
    weights = {"python": 40, "c++": 40, "web development": 20, "javascript": 10}
    score = 0
    matched = []
    skills_text_lower = skills_text.lower()
    
    for skill, points in weights.items():
        if skill in skills_text_lower:
            score += points
            matched.append(skill.capitalize())
            
    status = "SHORTLISTED" if score >= 60 else "REJECTED"
    
    return (f"Evaluation for {candidate_name}: Score {score}/100. "
            f"Matched: {', '.join(matched)}. STATUS: {status}. "
            f"{'Please ask the user to schedule an interview.' if status == 'SHORTLISTED' else 'Do not proceed.'}")

@tool
def tool_schedule_interview(candidate_name: str, date: str) -> str:
    """Schedules an interview while checking for existing calendar conflicts."""
    for slot in BOOKED_SLOTS:
        if slot.lower() in date.lower():
            return f"Conflict: {date} is already fully booked in the calendar. Please ask for another date."
    
    BOOKED_SLOTS.append(date)
    return f"Success: Interview officially confirmed for {candidate_name} on {date}."

@tool
def tool_get_hr_policy(action_or_topic: str, candidate_name: str = "") -> str:
    """
    DUAL PURPOSE TOOL: Use this for BOTH policy questions AND onboarding management.
    1. For HR Policy: Pass the topic to 'action_or_topic' and leave 'candidate_name' blank.
    2. For Onboarding: Pass 'status' or 'complete_docs' to 'action_or_topic' AND provide the 'candidate_name'.
    """
    # --- 1. THE ONBOARDING LOGIC ---
    if candidate_name:
        name = candidate_name.capitalize()
        if name not in ONBOARDING_DB:
            return f"Record Not Found: {name} is not currently in the onboarding pipeline."
        
        if action_or_topic == "status":
            s = ONBOARDING_DB[name]
            return (f"Onboarding Status for {name}: "
                    f"Documents: {'Done' if s['docs_submitted'] else 'Missing'}, "
                    f"Background Check: {s['background_check']}, "
                    f"Laptop: {'Assigned' if s['laptop_assigned'] else 'Not Sent'}.")
        
        if action_or_topic == "complete_docs":
            ONBOARDING_DB[name]["docs_submitted"] = True
            return f"Success: Onboarding Checklist updated. Documentation for {name} is now COMPLETE."
            
        return "Action Invalid. Please specify 'status' or 'complete_docs'."

    # --- 2. THE HR POLICY (RAG) LOGIC ---
    else:
        current_dir = os.path.dirname(__file__) 
        file_path = os.path.join(current_dir, "hr_handbook.txt")
        
        if not os.path.exists(file_path):
            return f"Error: HR Handbook file not found at {file_path}. Please check the src folder."
            
        try:
            with open(file_path, "r") as f:
                content = f.read()
            return f"Official Handbook Context:\n{content}\n\nUse this data to answer the specific query about '{action_or_topic}'."
        except Exception as e:
            return f"System Error reading handbook: {str(e)}"