# 🤖 Nasiko HR Automation Agent
### Built for the [Nasiko Buildathon](https://www.nasiko.com)

> **Nasiko** is an AI research lab building the intelligent agent registry and coordination platform — *"Shaping Agentic Systems of Tomorrow"*. This HR Agent is a Buildathon project built on top of Nasiko's agentic infrastructure.

---

## 📌 What is this?

An AI-powered HR automation agent that understands **natural language** and automates end-to-end HR workflows — from recruitment and candidate evaluation to onboarding, leave management, and policy queries.

No forms. No clicks. Just type what you want done.

---

## 🏗️ Tech Stack

| Layer | Technology |
|---|---|
| Agent Framework | LangChain (Tool-Calling Agent) |
| LLM | GPT-4o-mini (OpenAI) |
| API Server | FastAPI + Uvicorn |
| Protocol | JSON-RPC 2.0 (A2A format) |
| Containerization | Docker + Docker Compose |
| Data Persistence | JSON file (`hr_data.json`) |
| Language | Python 3.11 |

---

## 📁 Project Structure

```
src/
├── __main__.py       # FastAPI server, A2A request handling, conversation memory
├── agent.py          # LangChain agent setup, system prompt, tool registration
├── tools.py          # All 12 HR tools + DB + persistence logic
├── hr_handbook.txt   # Nasiko HR policy handbook (12 sections)
├── hr_data.json      # Auto-generated persistent data store
└── __init__.py
Dockerfile
docker-compose.yml
requirements.txt
```

---

## ⚡ Features

### 1. 🎯 Candidate Management
- Add new candidates with email, phone, skills
- Edit existing candidate profiles (email, phone, skills, status, notes)
- View full candidate details — status, score, interview schedule, notes

### 2. 🧠 Candidate Evaluation (AI Scoring)
- Skills-based scoring against 10 weighted skills:
  `Python(35) | C++(30) | Java(25) | ML(20) | JavaScript(20) | DevOps(15) | React(15) | Web Dev(15) | SQL(10) | Cloud(10)`
- Score ≥ 50 → **Shortlisted** | Score < 50 → **Rejected**
- Returns matched skills breakdown with points per skill

### 3. 📅 Interview Scheduling
- Schedule interviews with date, time, and optional interviewer name
- **Collision detection** — blocks double-booking the same slot
- Date (`YYYY-MM-DD`) and time (`HH:MM`) format validation

### 4. 📆 Interview Management
- List all interviews (filter by date or candidate)
- Check if a time slot is free
- Update interview status: `Scheduled / Completed / Cancelled / No-show`
- Record interview outcome and interviewer name
- Cancel interviews

### 5. 🎉 Hiring
- Hire shortlisted candidates in one command
- Auto-creates employee record with ID (`EMP####`)
- Initializes full leave balance (20 days) and onboarding checklist
- Blocks hiring rejected candidates with a clear error

### 6. 👥 Employee Management
- Add new employees (auto-generates Employee ID, email, leave balance)
- Edit employee fields: role, department, manager, joining date, status
- View full employee details — ID, role, dept, manager, joining date, leave balance

### 7. 🌴 Leave Management
- Check leave balance (total / used / remaining + recent history)
- Apply leave days with leave type: `Sick` or `Earned`
- Balance guard — rejects leave if insufficient days remaining
- Maintains full leave history per employee

### 8. ✅ Onboarding Checklist
- Track 7 onboarding items per employee:
  `docs | bg_check | laptop | id_card | bank_details | system_access | orientation`
- Mark individual items as complete
- Auto-detects when ALL items are done → 🎉 fully onboarded message

### 9. 📜 HR Policy Queries
- Reads from `hr_handbook.txt` (12 policy sections)
- Broad queries → returns all section names
- Specific queries → returns only that section's policies
- Never answers from memory — always reads live from the handbook file

### 10. 📋 List All
- List all employees, candidates, or interviews in one call
- Shows key info inline: role, dept, leave balance, score, status

### 11. 🔗 Pronoun / Context Resolution
- Tracks the last mentioned person in conversation
- Resolves `"him"`, `"her"`, `"his"`, `"their"` automatically
- e.g. "Check Mahesh's status" → "How many leaves does **he** have?" — works seamlessly

### 12. 💾 Data Persistence
- All changes auto-saved to `hr_data.json`
- Survives container restarts — data is not lost on reboot

### 13. 🧵 Multi-turn Conversation Memory
- Each `thread_id` maintains its own conversation history
- Context carries across multiple messages in the same session
- History trimmed to last 20 messages to prevent memory bloat

---

## 🚀 Setup & Run

### Prerequisites
- Docker & Docker Compose installed
- OpenAI API key

### 1. Clone & Configure
```bash
git clone <your-repo-url>
cd nasiko-hr-agent
cp .env.example .env
# Add your OPENAI_API_KEY to .env
```

### 2. Create Docker Network (first time only)
```bash
docker network create agents-net
```

### 3. Start the Agent
```bash
docker-compose up --build
```

Agent will be live at: `http://localhost:5000`

### 4. Health Check
```bash
curl http://localhost:5000/health
```

> ⚠️ **Deployment Note:** This agent is built for Nasiko's infrastructure. Due to a temporary technical issue on Nasiko's deployment end, the demo is being presented via terminal. The agent is fully functional and production-ready — only the live deployment step is pending infrastructure availability.

---

## 📡 API Reference

### Endpoint
```
POST http://localhost:5000/
Content-Type: application/json
```

### Request Format (JSON-RPC A2A)
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "message/send",
  "params": {
    "thread_id": "unique-session-id",
    "message": {
      "parts": [{ "kind": "text", "text": "Your prompt here" }]
    }
  }
}
```

### Response Format
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "result": {
    "kind": "task",
    "status": { "state": "completed", "timestamp": "..." },
    "artifacts": [
      { "kind": "text", "parts": [{ "kind": "text", "text": "Agent response here" }] }
    ]
  }
}
```

### PowerShell Quick Setup
```powershell
$base = "http://localhost:5000/"
$threadId = "my-session-001"

function Send-HR($prompt) {
    $json = @"
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "message/send",
  "params": {
    "thread_id": "$threadId",
    "message": {"parts": [{"kind": "text", "text": "$prompt"}]}
  }
}
"@
    (Invoke-RestMethod -Uri $base -Method POST -Body $json -ContentType "application/json").result.artifacts.parts.text
}
```

---

## 🗃️ Pre-loaded Demo Data

| Name | Type | Role / Status | Score |
|---|---|---|---|
| Mahesh | Employee | SDE-1, Engineering | — |
| Shreyash | Employee | SDE-1, Engineering | — |
| Ritesh | Candidate | Shortlisted | 80/100 |
| Karthik | Candidate | Shortlisted | 60/100 |
| Ananya | Candidate | Applied | 35/100 |
| Neha | Candidate | Rejected | 0/100 |

---

## 📚 HR Handbook — Policy Sections

| # | Section |
|---|---|
| 1 | Company Overview (Nasiko) |
| 2 | Office Hours & Attendance |
| 3 | Leave Policy |
| 4 | Compensation & Payroll |
| 5 | Health & Insurance |
| 6 | Onboarding |
| 7 | Travel Policy |
| 8 | Code of Conduct |
| 9 | Performance & Growth |
| 10 | Separation & Exit |
| 11 | Grievance & Escalation |
| 12 | IT & Data Security |

---

## 👨‍💻 Made with ❤️ by Team Prompt_maavale
Team participating in the **Nasiko Buildathon 2026**
Sponsored by [Nasiko](https://www.nasiko.com) — *Shaping Agentic Systems of Tomorrow*
