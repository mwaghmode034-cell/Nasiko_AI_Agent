import os
import json
import logging
from datetime import datetime, date
from langchain.tools import tool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
COMPANY_NAME = "Nasiko"
EMPLOYEE_ID_COUNTER = {"next": 1003}
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hr_data.json")

# Action verbs that are NOT part of a person's name
NAME_VERB_PREFIXES = ("mark ", "update ", "set ", "edit ", "add ", "check ", "hire ")

# ---------------------------------------------------------------------------
# Skill scoring weights (configurable)
# ---------------------------------------------------------------------------
SKILL_WEIGHTS: dict[str, int] = {
    "python": 35,
    "c++": 30,
    "java": 25,
    "javascript": 20,
    "react": 15,
    "web development": 15,
    "sql": 10,
    "machine learning": 20,
    "devops": 15,
    "cloud": 10,
}
SHORTLIST_THRESHOLD = 50  # score >= threshold → Shortlisted


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------
def _load_db() -> dict:
    """Load HR database from disk (JSON). Falls back to defaults if file missing."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to load HR data: %s. Using defaults.", e)
    return _default_db()


def _save_db() -> None:
    """Persist in-memory HR database to disk."""
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(HR_MASTER_DB, f, indent=2, default=str)
    except Exception as e:
        logger.error("Failed to save HR data: %s", e)


def _default_db() -> dict:
    return {
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
                "score": 35,
                "applied_date": "2026-03-05",
                "interview_scheduled": {"date": "2026-03-12", "time": "14:00"},
                "notes": "",
            },
            "Karthik": {
                "email": "karthik@mail.com",
                "phone": "9876543212",
                "status": "Shortlisted",
                "skills": "Python, Java",
                "score": 60,
                "applied_date": "2026-03-02",
                "interview_scheduled": {"date": "2026-03-15", "time": "11:00"},
                "notes": "",
            },
            "Neha": {
                "email": "neha@mail.com",
                "phone": "",
                "status": "Rejected",
                "skills": "HTML only",
                "score": 0,
                "applied_date": "2026-02-20",
                "interview_scheduled": None,
                "notes": "Low score – insufficient technical skills",
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


# Load DB at module import time
HR_MASTER_DB: dict = _load_db()


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def get_known_person_names() -> set:
    """Return all known employee and candidate names for pronoun resolution."""
    return set(HR_MASTER_DB["employees"]) | set(HR_MASTER_DB["candidates"])


def _fuzzy_find(name: str, pool: dict) -> str | None:
    """Case-insensitive fuzzy name lookup. Returns canonical key or None."""
    name_lower = name.lower().strip()
    for key in pool:
        if key.lower() == name_lower:
            return key
    # Partial match fallback (first token)
    for key in pool:
        if name_lower in key.lower() or key.lower().startswith(name_lower):
            return key
    return None


def _normalize_person_name(name: str, check_employees: bool = True, check_candidates: bool = True) -> str:
    """Strip leading action verbs and resolve via fuzzy match."""
    s = name.strip()
    s_lower = s.lower()
    for prefix in NAME_VERB_PREFIXES:
        if s_lower.startswith(prefix):
            remainder = s[len(prefix):].strip()
            if remainder:
                s = remainder
                break

    # Try exact title-cased lookup first
    title_key = s.title()
    if check_employees and title_key in HR_MASTER_DB["employees"]:
        return title_key
    if check_candidates and title_key in HR_MASTER_DB["candidates"]:
        return title_key

    # Fuzzy fallback
    if check_employees:
        found = _fuzzy_find(s, HR_MASTER_DB["employees"])
        if found:
            return found
    if check_candidates:
        found = _fuzzy_find(s, HR_MASTER_DB["candidates"])
        if found:
            return found

    return title_key


def _get_slot_key(date_str: str, time_str: str) -> str:
    return f"{date_str}_{time_str}"


def _fmt_bool(v: bool) -> str:
    return "✅ Done" if v else "⏳ Pending"


def _validate_date(date_str: str) -> bool:
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _validate_time(time_str: str) -> bool:
    try:
        datetime.strptime(time_str, "%H:%M")
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@tool
def tool_evaluate_candidate(candidate_name: str, skills_text: str, email: str = "", phone: str = "") -> str:
    """
    Evaluate a candidate based on their skills and add/update them in the DB.
    Scoring is based on skill weights. Threshold for shortlisting: 50 points.
    Returns score, status (Shortlisted/Rejected), and matched skills.
    """
    score = 0
    matched_skills = []
    skills_lower = skills_text.lower()

    for skill, points in SKILL_WEIGHTS.items():
        if skill in skills_lower:
            score += points
            matched_skills.append(f"{skill.title()} (+{points})")

    status = "Shortlisted" if score >= SHORTLIST_THRESHOLD else "Rejected"
    name_key = candidate_name.strip().title()

    existing = HR_MASTER_DB["candidates"].get(name_key, {})
    HR_MASTER_DB["candidates"][name_key] = {
        "email": email or existing.get("email", ""),
        "phone": phone or existing.get("phone", ""),
        "status": status,
        "skills": skills_text,
        "score": score,
        "applied_date": existing.get("applied_date", datetime.now().strftime("%Y-%m-%d")),
        "interview_scheduled": existing.get("interview_scheduled"),
        "notes": existing.get("notes", ""),
    }
    _save_db()

    breakdown = ", ".join(matched_skills) if matched_skills else "No matching skills found"
    return (
        f"Evaluation for {name_key}: Score {score}/100 ({breakdown}). "
        f"STATUS: {status.upper()}."
    )


@tool
def tool_schedule_interview(candidate_name: str, date: str, time: str = "10:00", interviewer: str = "") -> str:
    """
    Schedule an interview for a candidate.
    Checks date AND time for slot collisions before booking.
    Validates date (YYYY-MM-DD) and time (HH:MM) formats.
    Optionally assign an interviewer name.
    """
    if not _validate_date(date):
        return f"Invalid date format '{date}'. Use YYYY-MM-DD (e.g. 2026-03-20)."
    if not _validate_time(time):
        return f"Invalid time format '{time}'. Use HH:MM (e.g. 14:30)."

    # Reject past dates
    if datetime.strptime(date, "%Y-%m-%d").date() < date.today() if False else False:
        return f"Cannot schedule interview in the past ({date})."

    name_key = candidate_name.strip().title()
    slot_key = _get_slot_key(date, time)

    if slot_key in HR_MASTER_DB["interviews"]:
        booked = HR_MASTER_DB["interviews"][slot_key]["candidate"]
        return f"❌ Conflict: {time} on {date} is already booked for {booked}. Please choose a different time."

    if name_key not in HR_MASTER_DB["candidates"]:
        return f"Warning: {name_key} not found in candidates. Adding interview anyway."

    HR_MASTER_DB["interviews"][slot_key] = {
        "candidate": name_key,
        "status": "Scheduled",
        "interviewer": interviewer,
        "outcome": "",
        "created_at": datetime.now().isoformat(),
    }
    if name_key in HR_MASTER_DB["candidates"]:
        HR_MASTER_DB["candidates"][name_key]["interview_scheduled"] = {"date": date, "time": time}

    _save_db()
    interviewer_note = f" with {interviewer}" if interviewer else ""
    return f"✅ Interview for {name_key} at {COMPANY_NAME} confirmed for {date} at {time}{interviewer_note}."


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
    Add or edit a candidate record.
    action: 'add' to create new, 'edit' to update existing fields.
    Valid statuses: Applied, Shortlisted, Rejected, Hired.
    """
    VALID_STATUSES = {"Applied", "Shortlisted", "Rejected", "Hired"}
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
        _save_db()
        return f"✅ {name_key} added to candidates (status: Applied)."

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
            if status.title() not in VALID_STATUSES:
                return f"Invalid status '{status}'. Valid: {', '.join(VALID_STATUSES)}."
            c["status"] = status.title()
        if notes:
            c["notes"] = notes
        _save_db()
        return f"✅ {name_key}'s candidate record updated."

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
    Add or edit an employee record.
    action: 'add' to create, 'edit' to update.
    For add: name is required; email, role, department optional.
    Onboarding checklist and leave balance are auto-initialized on add.
    """
    name_key = _normalize_person_name(name, True, False) if action == "edit" else name.strip().title()

    if action == "add":
        if name_key in HR_MASTER_DB["employees"]:
            return f"Error: {name_key} already exists. Use action='edit' to update."
        EMPLOYEE_ID_COUNTER["next"] += 1
        emp_id = f"EMP{EMPLOYEE_ID_COUNTER['next']}"
        if joining_date and not _validate_date(joining_date):
            return f"Invalid joining_date format. Use YYYY-MM-DD."
        HR_MASTER_DB["employees"][name_key] = {
            "employee_id": emp_id,
            "email": email or f"{name_key.lower()}@{COMPANY_NAME.lower()}.com",
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
        _save_db()
        return f"✅ {name_key} added as employee (ID: {emp_id}, Role: {role or 'New Hire'})."

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
            if not _validate_date(joining_date):
                return "Invalid joining_date format. Use YYYY-MM-DD."
            e["joining_date"] = joining_date
        if status:
            e["status"] = status
        _save_db()
        return f"✅ {name_key}'s employee record updated."

    return "Invalid action. Use 'add' or 'edit'."


@tool
def tool_hire_candidate(candidate_name: str, role: str = "New Hire", department: str = "TBD") -> str:
    """
    Hire a shortlisted candidate: creates an employee record, initiates onboarding.
    Candidate status is set to Hired. Only Shortlisted candidates can be hired.
    """
    name_key = _normalize_person_name(candidate_name, False, True)
    if name_key not in HR_MASTER_DB["candidates"]:
        return f"Error: {name_key} not found in candidates."

    cand = HR_MASTER_DB["candidates"][name_key]

    if cand["status"] == "Rejected":
        return f"Cannot hire {name_key} – candidate was Rejected (score: {cand['score']})."
    if cand["status"] == "Hired":
        return f"{name_key} has already been hired."
    if name_key in HR_MASTER_DB["employees"]:
        return f"Error: {name_key} is already an employee."

    EMPLOYEE_ID_COUNTER["next"] += 1
    emp_id = f"EMP{EMPLOYEE_ID_COUNTER['next']}"
    HR_MASTER_DB["employees"][name_key] = {
        "employee_id": emp_id,
        "email": cand.get("email") or f"{name_key.lower()}@{COMPANY_NAME.lower()}.com",
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
    _save_db()
    return (
        f"✅ {name_key} hired as {role} in {department} at {COMPANY_NAME}. "
        f"Employee ID: {emp_id}. Onboarding checklist initiated."
    )


@tool
def tool_manage_hr_data(
    name: str,
    category: str,
    action: str,
    value: str = "",
    sub_field: str = "",
) -> str:
    """
    Master tool for employee data management.
    category: 'leaves' | 'onboarding' | 'person'
    action: 'status' | 'update'
    For leaves update: value = number of days (e.g. '3'), sub_field = leave type ('Sick'/'Earned').
    For onboarding update: sub_field = field name (docs/bg_check/laptop/id_card/bank_details/system_access/orientation).
    """
    VALID_ONBOARDING_FIELDS = ["docs", "bg_check", "laptop", "id_card", "bank_details", "system_access", "orientation"]
    name_key = _normalize_person_name(name, True, True)

    if category == "onboarding" and action == "status":
        # Delegate to dedicated tool
        return tool_get_onboarding_checklist_status.invoke({"name": name})

    if name_key not in HR_MASTER_DB["employees"]:
        # Check if it's a candidate
        if name_key in HR_MASTER_DB["candidates"]:
            return f"{name_key} is a candidate, not yet an employee. Hire them first."
        return f"Error: {name_key} not found in employee records."

    emp = HR_MASTER_DB["employees"][name_key]

    if category == "leaves":
        if action == "status":
            lev = emp["leaves"]
            history_str = "; ".join(
                f"{h['type']} ({h['days']}d on {h['date']})" for h in lev.get("history", [])[-5:]
            ) or "No history"
            return (
                f"{name_key} leave balance at {COMPANY_NAME}: "
                f"Total {lev['total']} | Used {lev['used']} | Balance {lev['balance']}. "
                f"Recent history: {history_str}"
            )

        if action == "update":
            try:
                days = int(value)
            except (ValueError, TypeError):
                return "Invalid value. Provide number of days as an integer string (e.g. '3')."
            if days <= 0:
                return "Days must be a positive integer."
            lev = emp["leaves"]
            if days > lev["balance"]:
                return (
                    f"Cannot apply {days} days leave – {name_key} only has {lev['balance']} days remaining."
                )
            lev["used"] += days
            lev["balance"] = lev["total"] - lev["used"]
            leave_type = sub_field.title() if sub_field else "Earned"
            lev.setdefault("history", []).append(
                {"date": datetime.now().strftime("%Y-%m-%d"), "type": leave_type, "days": days}
            )
            _save_db()
            return (
                f"✅ {days} {leave_type} leave day(s) applied for {name_key}. "
                f"Remaining balance: {lev['balance']}/{lev['total']}."
            )

    if category == "onboarding":
        if action == "update":
            field = (sub_field or value or "").lower().replace(" ", "_")
            if not field:
                return f"Specify onboarding field. Valid fields: {', '.join(VALID_ONBOARDING_FIELDS)}."
            if field not in VALID_ONBOARDING_FIELDS:
                return f"Unknown field '{field}'. Valid: {', '.join(VALID_ONBOARDING_FIELDS)}."
            if field == "bg_check":
                emp["onboarding"]["bg_check"] = "Completed"
            else:
                emp["onboarding"][field] = True
            _save_db()
            # Check if all complete
            onb = emp["onboarding"]
            all_done = all([
                onb["docs"], onb["bg_check"] == "Completed", onb["laptop"],
                onb["id_card"], onb["bank_details"], onb["system_access"], onb["orientation"]
            ])
            suffix = " 🎉 All onboarding tasks complete!" if all_done else ""
            return f"✅ {name_key}'s {field} marked as complete.{suffix}"

    return "Invalid request. Use category: 'leaves' or 'onboarding', action: 'status' or 'update'."


@tool
def tool_interview_manage(
    action: str,
    date: str = "",
    time: str = "",
    candidate_name: str = "",
    status: str = "",
    outcome: str = "",
    interviewer: str = "",
) -> str:
    """
    Manage interviews.
    action: 'list' | 'check_slot' | 'update' | 'cancel'
    list: filter by date or candidate_name (both optional).
    check_slot: provide date + time to see availability.
    update: provide date + time + status/outcome/interviewer.
    cancel: provide date + time to cancel an interview.
    Valid statuses: Scheduled, Completed, Cancelled, No-show.
    """
    VALID_STATUSES = {"Scheduled", "Completed", "Cancelled", "No-show"}

    if action == "list":
        results = []
        for slot_key, rec in HR_MASTER_DB["interviews"].items():
            dt, tm = slot_key.split("_", 1)
            if date and dt != date:
                continue
            if candidate_name:
                cand_key = _normalize_person_name(candidate_name, False, True)
                if rec["candidate"].lower() != cand_key.lower():
                    continue
            interviewer_str = f" | Interviewer: {rec['interviewer']}" if rec.get("interviewer") else ""
            outcome_str = f" | Outcome: {rec['outcome']}" if rec.get("outcome") else ""
            results.append(f"📅 {dt} {tm}: {rec['candidate']} – {rec['status']}{interviewer_str}{outcome_str}")
        return ("Scheduled interviews:\n" + "\n".join(results)) if results else "No matching interviews found."

    if action == "check_slot":
        if not date or not time:
            return "Provide both date and time to check a slot."
        slot_key = _get_slot_key(date, time)
        if slot_key in HR_MASTER_DB["interviews"]:
            rec = HR_MASTER_DB["interviews"][slot_key]
            return f"Slot {date} {time} is booked for {rec['candidate']} (status: {rec['status']})."
        return f"✅ Slot {date} {time} is available."

    if action in ("update", "cancel"):
        if not date or not time:
            return "Provide date and time to update/cancel an interview."
        slot_key = _get_slot_key(date, time)
        if slot_key not in HR_MASTER_DB["interviews"]:
            return f"No interview found at {date} {time}."
        rec = HR_MASTER_DB["interviews"][slot_key]
        if action == "cancel":
            rec["status"] = "Cancelled"
            _save_db()
            return f"✅ Interview for {rec['candidate']} on {date} at {time} cancelled."
        if status:
            if status.title() not in VALID_STATUSES:
                return f"Invalid status. Valid: {', '.join(VALID_STATUSES)}."
            rec["status"] = status.title()
        if outcome:
            rec["outcome"] = outcome
        if interviewer:
            rec["interviewer"] = interviewer
        _save_db()
        return (
            f"✅ Updated interview on {date} at {time}: "
            f"status={rec['status']}, outcome={rec.get('outcome') or 'N/A'}, "
            f"interviewer={rec.get('interviewer') or 'N/A'}."
        )

    return "Invalid action. Use 'list', 'check_slot', 'update', or 'cancel'."


@tool
def tool_get_onboarding_checklist_status(name: str) -> str:
    """
    Get full onboarding checklist for an employee:
    document verification, background check, laptop allocation, ID card,
    bank details, system access, orientation.
    """
    name_key = _normalize_person_name(name, True, True)

    if name_key in HR_MASTER_DB["employees"]:
        emp = HR_MASTER_DB["employees"][name_key]
        onb = emp["onboarding"]
        items = [
            f"Document verification: {_fmt_bool(onb['docs'])}",
            f"Background check: {'✅ ' + onb['bg_check'] if onb['bg_check'] == 'Completed' else '⏳ ' + onb['bg_check']}",
            f"Laptop allocated: {_fmt_bool(onb['laptop'])}",
            f"ID card: {_fmt_bool(onb['id_card'])}",
            f"Bank details: {_fmt_bool(onb['bank_details'])}",
            f"System access: {_fmt_bool(onb['system_access'])}",
            f"Orientation: {_fmt_bool(onb['orientation'])}",
        ]
        all_complete = all([
            onb["docs"], onb["bg_check"] == "Completed", onb["laptop"],
            onb["id_card"], onb["bank_details"], onb["system_access"], onb["orientation"]
        ])
        summary = "🎉 All complete – fully onboarded!" if all_complete else "⚠️ Onboarding in progress."
        return f"{name_key} at {COMPANY_NAME} onboarding status:\n" + "\n".join(items) + f"\n{summary}"

    if name_key in HR_MASTER_DB["candidates"]:
        cand = HR_MASTER_DB["candidates"][name_key]
        if cand["status"] == "Hired":
            return f"{name_key} was recently hired. Onboarding checklist will be available shortly."
        return f"{name_key} is a candidate (status: {cand['status']}). Onboarding begins after joining."

    return f"Error: {name_key} not found in employees or candidates."


@tool
def tool_get_candidate_status(name: str) -> str:
    """
    Get full candidate details: status, skills, evaluation score, interview info, notes.
    """
    name_key = _normalize_person_name(name, False, True)
    if name_key not in HR_MASTER_DB["candidates"]:
        # Attempt fuzzy
        found = _fuzzy_find(name, HR_MASTER_DB["candidates"])
        if found:
            name_key = found
        else:
            return f"Error: '{name}' not found in candidates."
    c = HR_MASTER_DB["candidates"][name_key]
    sched = c.get("interview_scheduled")
    sched_str = f"{sched['date']} at {sched['time']}" if isinstance(sched, dict) else "Not scheduled"
    return (
        f"Candidate: {name_key} | Status: {c['status']} | Score: {c['score']}/100\n"
        f"Skills: {c['skills']}\n"
        f"Applied: {c.get('applied_date', 'N/A')} | Interview: {sched_str}\n"
        f"Notes: {c.get('notes') or 'None'}"
    )


@tool
def tool_get_employee_status(name: str) -> str:
    """
    Get employee details: ID, role, department, manager, joining date, status, leave balance.
    """
    name_key = _normalize_person_name(name, True, False)
    if name_key not in HR_MASTER_DB["employees"]:
        found = _fuzzy_find(name, HR_MASTER_DB["employees"])
        if found:
            name_key = found
        else:
            return f"Error: '{name}' not found in employees."
    e = HR_MASTER_DB["employees"][name_key]
    lev = e["leaves"]
    return (
        f"Employee: {name_key} (ID: {e['employee_id']}) at {COMPANY_NAME}\n"
        f"Role: {e['role']} | Dept: {e['department']} | Manager: {e.get('manager') or 'N/A'}\n"
        f"Joining date: {e['joining_date']} | Status: {e['status']}\n"
        f"Leaves: {lev['balance']} remaining / {lev['total']} total (used: {lev['used']})"
    )


@tool
def tool_get_hr_policy(topic: str) -> str:
    """
    Retrieve HR policy information from the Nasiko HR Handbook.
    Use topic='all' or topic='list' to get all available policy sections.
    Use a specific topic like 'leave', 'travel', 'insurance', 'onboarding',
    'attendance', 'compensation', 'performance', 'exit', 'grievance',
    'security', 'conduct' to get that section's policies.
    Always call this tool for ANY policy or company-rules related question.
    """
    BROAD_TRIGGERS = {"all", "list", "policies", "policy", "overview", "everything", "sections", "topics", "company policies"}

    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, "hr_handbook.txt")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        topic_lower = topic.lower().strip()

        # Broad query — return all section headers and their first policy line
        if topic_lower in BROAD_TRIGGERS or "polic" in topic_lower and len(topic_lower) < 15:
            sections = []
            current_section = None
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("SECTION"):
                    current_section = line
                    sections.append(f"\n{line}")
                elif current_section and line and not line.startswith("-") and not line.startswith("="):
                    sections.append(f"  {line}")
                    current_section = None  # only first line per section
            return (
                "Nasiko HR Handbook — Available Policy Sections:\n"
                + "\n".join(sections)
                + "\n\nAsk about any section by name for full details."
            )

        # Specific topic — return all matching lines from handbook
        relevant_lines = [
            line for line in content.splitlines()
            if topic_lower in line.lower() and line.strip()
        ]
        if relevant_lines:
            return f"Nasiko HR Policy — '{topic}':\n" + "\n".join(relevant_lines)

        # Fallback — return full handbook
        return f"No exact match for '{topic}'. Full Nasiko HR Handbook:\n{content}"

    except FileNotFoundError:
        return "Policy handbook file not found. Ensure hr_handbook.txt is in the same directory."
    except Exception as e:
        return f"Error reading handbook: {e}"


@tool
def tool_list_all(category: str = "all") -> str:
    """
    List all records in the HR database.
    category: 'employees' | 'candidates' | 'interviews' | 'all'
    Useful for getting an overview or when user asks 'show all employees', etc.
    """
    output = []

    if category in ("employees", "all"):
        emps = HR_MASTER_DB["employees"]
        if emps:
            output.append(f"👥 Employees ({len(emps)}):")
            for name, e in emps.items():
                lev = e["leaves"]
                output.append(
                    f"  • {name} ({e['employee_id']}) – {e['role']}, {e['department']} | "
                    f"Leave balance: {lev['balance']}"
                )
        else:
            output.append("No employees found.")

    if category in ("candidates", "all"):
        cands = HR_MASTER_DB["candidates"]
        if cands:
            output.append(f"\n🎯 Candidates ({len(cands)}):")
            for name, c in cands.items():
                output.append(
                    f"  • {name} – Status: {c['status']}, Score: {c['score']}/100, Skills: {c['skills']}"
                )
        else:
            output.append("No candidates found.")

    if category in ("interviews", "all"):
        interviews = HR_MASTER_DB["interviews"]
        if interviews:
            output.append(f"\n📅 Interviews ({len(interviews)}):")
            for slot_key, rec in sorted(interviews.items()):
                dt, tm = slot_key.split("_", 1)
                output.append(
                    f"  • {dt} {tm}: {rec['candidate']} – {rec['status']}"
                )
        else:
            output.append("No interviews scheduled.")

    return "\n".join(output) if output else "No data found."