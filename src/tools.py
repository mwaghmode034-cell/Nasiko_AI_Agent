import os
from langchain.tools import tool

# Mock Database for Scheduling
BOOKED_SLOTS = ["March 12", "March 15"]

@tool
def tool_evaluate_candidate(candidate_name: str, skills_text: str) -> str:
    """Evaluates a candidate based on weighted technical scoring."""
    # Define weights for different skills
    weights = {
        "python": 40,
        "c++": 40,
        "web development": 20,
        "javascript": 10
    }
    
    score = 0
    matched = []
    skills_text_lower = skills_text.lower()
    
    for skill, points in weights.items():
        if skill in skills_text_lower:
            score += points
            matched.append(skill.capitalize())
            
    # Decision logic based on score (Pass threshold: 60)
    status = "SHORTLISTED" if score >= 60 else "REJECTED"
    
    return (f"Evaluation for {candidate_name}: Score {score}/100. "
            f"Matched: {', '.join(matched)}. STATUS: {status}. "
            f"{'Suggest scheduling an interview.' if status == 'SHORTLISTED' else 'Do not proceed.'}")

@tool
def tool_schedule_interview(candidate_name: str, date: str) -> str:
    """Schedules an interview while checking for existing calendar conflicts."""
    # Simple logic to check if the date is already in our 'database'
    for slot in BOOKED_SLOTS:
        if slot.lower() in date.lower():
            return f"Conflict Error: {date} is already fully booked. Please ask the candidate for a different date."
    
    # If no conflict, add to booked slots
    BOOKED_SLOTS.append(date)
    return f"Success: Interview officially confirmed for {candidate_name} on {date}."

@tool
def tool_get_hr_policy(topic: str) -> str:
    """Retrieves the HR Handbook content so the agent can answer policy questions."""
    import os
    current_dir = os.path.dirname(__file__) 
    file_path = os.path.join(current_dir, "hr_handbook.txt")
    
    if not os.path.exists(file_path):
        return f"Error: HR Handbook file not found at {file_path}."
        
    try:
        # Just grab the whole file and hand it to the LLM
        with open(file_path, "r") as f:
            content = f.read()
        return f"Here is the official handbook. Read it and answer the question about '{topic}':\n\n{content}"
    except Exception as e:
        return f"Error reading file: {str(e)}"