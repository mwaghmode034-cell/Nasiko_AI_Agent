import os
from datetime import datetime
from langchain.tools import tool

# --- UNIFIED HR MASTER DATABASE (Extended Schema) ---
COMPANY_NAME = "Nasiko"
EMPLOYEE_ID_COUNTER = {"next": 1003}

# Action verbs that are NOT part of a person's name (e.g. "Mark Mahesh" -> name is "Mahesh")
NAME_VERB_PREFIXES = ("mark ", "update ", "set ", "edit ", "add ", "check ")

HR_MASTER_DB = {
    "employees": {
        "Mahesh": {
            "employee_id": "EMP1001",
            "email": "mahesh@company.com",
            "role": "SDE-1",
            "department": "Engineering",
            "manager": "",
            "joining_date": "2025-09-01",
            "status": "Active",
            "leaves": {
                "total": 20,
                "used": 8,
                "balance": 12,
                "history": [
                    {"date": "2025-11-20", "type": "Earned", "days": 5},
                    {"date": "2026-01-10", "type": "Sick", "days": 3},
                ],
            },
            "onboarding": {
                "docs": True,
                "bg_check": "Completed",
                "laptop": True,
                "id_card": True,
                "bank_details": True,
                "system_access": True,
                "orientation": True,
            },
        },
        "Shreyash": {
            "employee_id": "EMP1002",
            "email": "shreyash@company.com",
            "role": "SDE-1",
            "department": "Engineering",
            "manager": "Mahesh",
            "joining_date": "2026-02-15",
            "status": "Active",
            "leaves": {
                "total": 20,
                "used": 0,
                "balance": 20,
                "history": [],
            },
            "onboarding": {
                "docs": False,
                "bg_check": "Pending",
                "laptop": False,
                "id_card": False,
                "bank_details": False,
                "system_access": False,
                "orientation": False,
            },
        },
    },
    "candidates": {
        "Ritesh": {
            "email": "ritesh@mail.com",
            "phone": "9876543210",
            "status": "Shortlisted",
            "skills": "Python, C++, Web Development",
            "score": 80,
            "applied_date": "2026-03-01",
            "interview_scheduled": {"date": "2026-03-12", "time": "10:00"},
            "notes": "",
        },
        "Ananya": {
            "email": "ananya@mail.com",
            "phone": "9876543211",
            "status": "Applied",
            "skills": "JavaScript, React",
            "score": 0,
            "applied_date": "2026-03-05",
            "interview_scheduled": {"date": "2026-03-12", "time": "14:00"},
            "notes": "",
        },
        "Karthik": {
            "email": "karthik@mail.com",
            "phone": "9876543212",
            "status": "Shortlisted",
            "skills": "Python, Java",
            "score": 70,
            "applied_date": "2026-03-02",
            "interview_scheduled": {"date": "2026-03-15", "time": "11:00"},
            "notes": "",
        },
        "Neha": {
            "email": "neha@mail.com",
            "phone": "",
            "status": "Rejected",
            "skills": "HTML only",
            "score": 20,
            "applied_date": "2026-02-20",
            "interview_scheduled": None,
            "notes": "Low score",
        },
    },
    "interviews": {
        "2026-03-12_10:00": {
            "candidate": "Ritesh",
            "status": "Scheduled",
            "interviewer": "",
            "outcome": "",
        },
        "2026-03-12_14:00": {
            "candidate": "Ananya",
            "status": "Scheduled",
            "interviewer": "",
            "outcome": "",
        },
        "2026-03-15_11:00": {
            "candidate": "Karthik",
            "status": "Scheduled",
            "interviewer": "",
            "outcome": "",
        },
    },
}


def get_known_person_names():
    """Return set of all known employee and candidate names for pronoun resolution."""
    emp = set(HR_MASTER_DB["employees"].keys())
    cand = set(HR_MASTER_DB["candidates"].keys())
    return emp | cand


def _normalize_person_name(name: str, check_employees: bool = True, check_candidates: bool = True) -> str:
    """Strip leading action verbs (Mark, Update, etc.) when remainder exists in DB. 'Mark Mahesh' -> 'Mahesh'."""
    s = name.strip()
    s_lower = s.lower()
    for prefix in NAME_VERB_PREFIXES:
        if s_lower.startswith(prefix):
            remainder = s[len(prefix) :].strip()
            if not remainder:
                break
            key = remainder.title()
            if check_employees and key in HR_MASTER_DB["employees"]:
                return key
            if check_candidates and key in HR_MASTER_DB["candidates"]:
                return key
            break  # Remainder not in DB - don't strip (e.g. "Mark Johnson" is a real name)
    return s.title()


def _get_slot_key(date: str, time: str) -> str:
    """Returns slot key for collision check: date_time"""
    return f"{date}_{time}"


def _fmt_bool(v: bool) -> str:
    """Format boolean as Done/Pending."""
    return "Done" if v else "Pending"


@tool
def tool_evaluate_candidate(candidate_name: str, skills_text: str, email: str = "", phone: str = "") -> str:
    """Evaluates a candidate and adds/updates them in the candidate database. Optionally include email and phone."""
    weights = {"python": 40, "c++": 40, "web development": 20, "javascript": 10}
    score = 0
    skills_text_lower = skills_text.lower()
    for skill, points in weights.items():
        if skill in skills_text_lower:
            score += points

    status = "SHORTLISTED" if score >= 60 else "REJECTED"
    name_key = candidate_name.strip().title()
    HR_MASTER_DB["candidates"][name_key] = {
        "email": email or HR_MASTER_DB["candidates"].get(name_key, {}).get("email", ""),
        "phone": phone or HR_MASTER_DB["candidates"].get(name_key, {}).get("phone", ""),
        "status": status,
        "skills": skills_text,
        "score": score,
        "applied_date": HR_MASTER_DB["candidates"].get(name_key, {}).get("applied_date", datetime.now().strftime("%Y-%m-%d")),
        "interview_scheduled": HR_MASTER_DB["candidates"].get(name_key, {}).get("interview_scheduled"),
        "notes": HR_MASTER_DB["candidates"].get(name_key, {}).get("notes", ""),
    }
    return f"Evaluation for {name_key}: Score {score}/100. STATUS: {status}."


@tool
def tool_schedule_interview(candidate_name: str, date: str, time: str = "10:00") -> str:
    """Schedules an interview. Checks BOTH date AND time for collision. Use slot_key internally."""
    name_key = candidate_name.strip().title()
    slot_key = _get_slot_key(date, time)

    if slot_key in HR_MASTER_DB["interviews"]:
        return f"Conflict: {time} on {date} is already booked. Please suggest a different time."

    HR_MASTER_DB["interviews"][slot_key] = {
        "candidate": name_key,
        "status": "Scheduled",
        "interviewer": "",
        "outcome": "",
    }

    # Update candidate's interview_scheduled
    if name_key in HR_MASTER_DB["candidates"]:
        HR_MASTER_DB["candidates"][name_key]["interview_scheduled"] = {"date": date, "time": time}

    return f"Success: Interview for {name_key} at {COMPANY_NAME} confirmed for {date} at {time}."


@tool
def tool_add_edit_candidate(
    name: str,
    action: str,
    email: str = "",
    phone: str = "",
    skills: str = "",
    status: str = "",
    notes: str = "",
) -> str:
    """
    Add or edit a candidate.
    action: 'add' (create new) or 'edit' (update existing)
    For add: provide name, optionally email, phone, skills.
    For edit: provide name and any fields to update (email, phone, skills, status, notes).
    """
    name_key = _normalize_person_name(name, False, True) if action == "edit" else name.strip().title()

    if action == "add":
        if name_key in HR_MASTER_DB["candidates"]:
            return f"Error: {name_key} already exists. Use action='edit' to update."
        HR_MASTER_DB["candidates"][name_key] = {
            "email": email,
            "phone": phone,
            "status": "Applied",
            "skills": skills,
            "score": 0,
            "applied_date": datetime.now().strftime("%Y-%m-%d"),
            "interview_scheduled": None,
            "notes": notes,
        }
        return f"Success: {name_key} added to candidates."

    if action == "edit":
        if name_key not in HR_MASTER_DB["candidates"]:
            return f"Error: {name_key} not found in candidates."
        c = HR_MASTER_DB["candidates"][name_key]
        if email:
            c["email"] = email
        if phone:
            c["phone"] = phone
        if skills:
            c["skills"] = skills
        if status:
            c["status"] = status
        if notes:
            c["notes"] = notes
        return f"Success: {name_key} updated."

    return "Invalid action. Use 'add' or 'edit'."


@tool
def tool_add_edit_employee(
    name: str,
    action: str,
    email: str = "",
    role: str = "",
    department: str = "",
    manager: str = "",
    joining_date: str = "",
    status: str = "",
) -> str:
    """
    Add or edit an employee.
    action: 'add' (create new) or 'edit' (update existing)
    For add: provide name, optionally email, role, department. Onboarding and leaves initialized.
    For edit: provide name and any fields to update.
    """
    name_key = _normalize_person_name(name, True, False) if action == "edit" else name.strip().title()

    if action == "add":
        if name_key in HR_MASTER_DB["employees"]:
            return f"Error: {name_key} already exists. Use action='edit' to update."
        EMPLOYEE_ID_COUNTER["next"] += 1
        emp_id = f"EMP{EMPLOYEE_ID_COUNTER['next']}"
        HR_MASTER_DB["employees"][name_key] = {
            "employee_id": emp_id,
            "email": email or f"{name_key.lower()}@company.com",
            "role": role or "New Hire",
            "department": department or "TBD",
            "manager": manager or "",
            "joining_date": joining_date or datetime.now().strftime("%Y-%m-%d"),
            "status": "Active",
            "leaves": {"total": 20, "used": 0, "balance": 20, "history": []},
            "onboarding": {
                "docs": False,
                "bg_check": "Pending",
                "laptop": False,
                "id_card": False,
                "bank_details": False,
                "system_access": False,
                "orientation": False,
            },
        }
        return f"Success: {name_key} added as employee with ID {emp_id}."

    if action == "edit":
        if name_key not in HR_MASTER_DB["employees"]:
            return f"Error: {name_key} not found in employees."
        e = HR_MASTER_DB["employees"][name_key]
        if email:
            e["email"] = email
        if role:
            e["role"] = role
        if department:
            e["department"] = department
        if manager:
            e["manager"] = manager
        if joining_date:
            e["joining_date"] = joining_date
        if status:
            e["status"] = status
        return f"Success: {name_key} updated."

    return "Invalid action. Use 'add' or 'edit'."


@tool
def tool_hire_candidate(candidate_name: str, role: str = "New Hire", department: str = "TBD") -> str:
    """Hires a shortlisted candidate: creates employee record, sets onboarding status. Candidate status set to Hired."""
    name_key = _normalize_person_name(candidate_name, False, True)
    if name_key not in HR_MASTER_DB["candidates"]:
        return f"Error: {name_key} not found in candidates."
    cand = HR_MASTER_DB["candidates"][name_key]
    if name_key in HR_MASTER_DB["employees"]:
        return f"Error: {name_key} is already an employee."

    EMPLOYEE_ID_COUNTER["next"] += 1
    emp_id = f"EMP{EMPLOYEE_ID_COUNTER['next']}"
    HR_MASTER_DB["employees"][name_key] = {
        "employee_id": emp_id,
        "email": cand.get("email") or f"{name_key.lower()}@company.com",
        "role": role,
        "department": department,
        "manager": "",
        "joining_date": datetime.now().strftime("%Y-%m-%d"),
        "status": "Active",
        "leaves": {"total": 20, "used": 0, "balance": 20, "history": []},
        "onboarding": {
            "docs": False,
            "bg_check": "Pending",
            "laptop": False,
            "id_card": False,
            "bank_details": False,
            "system_access": False,
            "orientation": False,
        },
    }
    cand["status"] = "Hired"
    return f"Success: {name_key} hired as {role} at {COMPANY_NAME}. Employee ID: {emp_id}. Onboarding initiated."


@tool
def tool_manage_hr_data(
    name: str,
    category: str,
    action: str,
    value: str = "",
    sub_field: str = "",
) -> str:
    """
    Master tool for employee data: leaves, onboarding, and person edits.
    category: 'leaves' | 'onboarding' | 'person'
    action: 'status' | 'update' | 'add_new'
    For onboarding update: use sub_field like 'docs', 'bg_check', 'laptop', 'id_card', 'bank_details', 'system_access', 'orientation'
    For leaves update: value = number of days to add (e.g. '3'). Optionally sub_field = leave type like 'Sick' or 'Earned'.
    """
    name_key = _normalize_person_name(name, True, True)

    # Onboarding status: show document verification, laptop allocation, and other checklist items
    if category == "onboarding" and action == "status":
        if name_key in HR_MASTER_DB["employees"]:
            emp = HR_MASTER_DB["employees"][name_key]
            onb = emp["onboarding"]
            checklist = (
                f"Document verification: {_fmt_bool(onb['docs'])} | "
                f"Background check: {onb['bg_check']} | "
                f"Laptop allocated: {_fmt_bool(onb['laptop'])} | "
                f"ID card: {_fmt_bool(onb['id_card'])} | "
                f"Bank details: {_fmt_bool(onb['bank_details'])} | "
                f"System access: {_fmt_bool(onb['system_access'])} | "
                f"Orientation: {_fmt_bool(onb['orientation'])}"
            )
            all_complete = all(
                (onb["docs"], onb["bg_check"] == "Completed", onb["laptop"], onb["id_card"],
                 onb["bank_details"], onb["system_access"], onb["orientation"])
            )
            if all_complete:
                return f"{name_key} at {COMPANY_NAME}: {checklist}. All complete - has joined."
            return f"{name_key} at {COMPANY_NAME}: {checklist}."
        if name_key in HR_MASTER_DB["candidates"]:
            cand = HR_MASTER_DB["candidates"][name_key]
            if cand["status"] == "Hired":
                return f"{name_key} has just joined {COMPANY_NAME}."
            return f"{name_key} is a candidate at {COMPANY_NAME}. Onboarding will begin after they accept the offer and join."
        return f"Error: {name_key} not found in employees or candidates."

    if action == "add_new" and category == "person":
        return "Use tool_add_edit_employee with action='add' to add a new employee."

    if name_key not in HR_MASTER_DB["employees"]:
        return f"Error: {name_key} not found in Employee records."

    emp = HR_MASTER_DB["employees"][name_key]

    if category == "leaves":
        if action == "status":
            lev = emp["leaves"]
            return (
                f"{name_key} at {COMPANY_NAME}: Total {lev['total']}, Used {lev['used']}, Balance {lev['balance']}. "
                f"History: {lev.get('history', [])}"
            )
        if action == "update":
            days = int(value) if value else 0
            lev = emp["leaves"]
            lev["used"] += days
            lev["balance"] = lev["total"] - lev["used"]
            leave_type = sub_field or "Earned"
            lev.setdefault("history", []).append(
                {"date": datetime.now().strftime("%Y-%m-%d"), "type": leave_type, "days": days}
            )
            return f"Updated: {name_key} has used {days} more leave days. Balance: {lev['balance']}."

    if category == "onboarding":
        if action == "update":
            valid = ["docs", "bg_check", "laptop", "id_card", "bank_details", "system_access", "orientation"]
            field = sub_field or value
            if not field:
                return "Specify onboarding field to update (docs, bg_check, laptop, etc.)."
            field_lower = field.lower().replace(" ", "_")
            if field_lower in valid:
                if field_lower == "bg_check":
                    emp["onboarding"][field_lower] = "Completed" if (value and value.lower() == "complete") else value or "Completed"
                else:
                    emp["onboarding"][field_lower] = True
                return f"Success: {name_key}'s {field_lower} is now updated."
            if value == "complete_docs":
                emp["onboarding"]["docs"] = True
                return f"Success: {name_key}'s documentation marked as COMPLETE."
            return f"Unknown onboarding field. Valid: {valid}"

    return "Invalid request. Use category: leaves, onboarding, or person."


@tool
def tool_interview_manage(action: str, date: str = "", time: str = "", candidate_name: str = "", status: str = "", outcome: str = "") -> str:
    """
    Manage interviews: list, check slot, update status/outcome.
    action: 'list' | 'check_slot' | 'update'
    For list: returns all scheduled interviews. Optionally filter by date or candidate_name.
    For check_slot: provide date and time to check if slot is free.
    For update: provide date, time, and status (Scheduled/Completed/Cancelled/No-show) or outcome.
    """
    if action == "list":
        slots = []
        for slot_key, rec in HR_MASTER_DB["interviews"].items():
            dt, tm = slot_key.split("_", 1)
            if date and dt != date:
                continue
            if candidate_name:
                cand_key = _normalize_person_name(candidate_name, False, True)
                if rec["candidate"].lower() != cand_key.lower():
                    continue
            slots.append(f"{dt} {tm}: {rec['candidate']} - {rec['status']}")
        return "Interviews:\n" + "\n".join(slots) if slots else "No matching interviews."

    if action == "check_slot":
        if not date or not time:
            return "Provide date and time to check slot."
        slot_key = _get_slot_key(date, time)
        if slot_key in HR_MASTER_DB["interviews"]:
            rec = HR_MASTER_DB["interviews"][slot_key]
            return f"Slot {date} {time} is booked by {rec['candidate']} (status: {rec['status']})."
        return f"Slot {date} {time} is available."

    if action == "update":
        if not date or not time:
            return "Provide date and time to update interview."
        slot_key = _get_slot_key(date, time)
        if slot_key not in HR_MASTER_DB["interviews"]:
            return f"No interview found for {date} at {time}."
        rec = HR_MASTER_DB["interviews"][slot_key]
        if status:
            rec["status"] = status
        if outcome:
            rec["outcome"] = outcome
        return f"Updated: {date} {time} - status={rec['status']}, outcome={rec.get('outcome', '')}."

    return "Invalid action. Use 'list', 'check_slot', or 'update'."


@tool
def tool_get_onboarding_checklist_status(name: str) -> str:
    """
    Get onboarding checklist status: document verification, laptop allocation, id card,
    bank details, system access, orientation. Use for queries about document verification,
    laptop allocation, or onboarding progress.
    """
    name_key = _normalize_person_name(name, True, True)
    if name_key in HR_MASTER_DB["employees"]:
        emp = HR_MASTER_DB["employees"][name_key]
        onb = emp["onboarding"]
        checklist = (
            f"{name_key} at {COMPANY_NAME}: "
            f"Document verification: {_fmt_bool(onb['docs'])} | "
            f"Background check: {onb['bg_check']} | "
            f"Laptop allocated: {_fmt_bool(onb['laptop'])} | "
            f"ID card: {_fmt_bool(onb['id_card'])} | "
            f"Bank details: {_fmt_bool(onb['bank_details'])} | "
            f"System access: {_fmt_bool(onb['system_access'])} | "
            f"Orientation: {_fmt_bool(onb['orientation'])}"
        )
        all_complete = all(
            (onb["docs"], onb["bg_check"] == "Completed", onb["laptop"], onb["id_card"],
             onb["bank_details"], onb["system_access"], onb["orientation"])
        )
        if all_complete:
            return f"{checklist}. All complete."
        return checklist
    if name_key in HR_MASTER_DB["candidates"]:
        cand = HR_MASTER_DB["candidates"][name_key]
        if cand["status"] == "Hired":
            return f"{name_key} has just joined {COMPANY_NAME}."
        return f"{name_key} is a candidate. Onboarding begins after they join {COMPANY_NAME}."
    return f"Error: {name_key} not found."


@tool
def tool_get_candidate_status(name: str) -> str:
    """Get full candidate details: status, skills, score, interview scheduled, notes."""
    name_key = _normalize_person_name(name, False, True)
    if name_key not in HR_MASTER_DB["candidates"]:
        return f"Error: {name_key} not found in candidates."
    c = HR_MASTER_DB["candidates"][name_key]
    sched = c.get("interview_scheduled")
    sched_str = f"{sched['date']} at {sched['time']}" if isinstance(sched, dict) else str(sched or "None")
    return (
        f"{name_key} (candidate at {COMPANY_NAME}): status={c['status']}, skills={c['skills']}, score={c['score']}, "
        f"applied={c.get('applied_date')}, interview={sched_str}, notes={c.get('notes', '')}"
    )


@tool
def tool_get_employee_status(name: str) -> str:
    """Get full employee details: role, department, leaves. Does NOT show onboarding (employees are already onboarded)."""
    name_key = _normalize_person_name(name, True, False)
    if name_key not in HR_MASTER_DB["employees"]:
        return f"Error: {name_key} not found in employees."
    e = HR_MASTER_DB["employees"][name_key]
    lev = e["leaves"]
    return (
        f"{name_key} (ID: {e['employee_id']}) at {COMPANY_NAME}: role={e['role']}, dept={e['department']}, "
        f"status={e['status']}, leaves={lev['balance']}/{lev['total']}"
    )


@tool
def tool_get_hr_policy(topic: str) -> str:
    """Retrieves standard policy info from the HR Handbook."""
    current_dir = os.path.dirname(__file__)
    file_path = os.path.join(current_dir, "hr_handbook.txt")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return f"Handbook Context for '{topic}':\n{content}"
    except Exception:
        return "Policy handbook not found."
