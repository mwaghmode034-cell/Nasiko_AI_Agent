import logging
from typing import List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain.agents import AgentExecutor, create_tool_calling_agent

from tools import (
    tool_evaluate_candidate,
    tool_schedule_interview,
    tool_get_hr_policy,
    tool_manage_hr_data,
    tool_add_edit_candidate,
    tool_add_edit_employee,
    tool_hire_candidate,
    tool_interview_manage,
    tool_get_candidate_status,
    tool_get_employee_status,
    tool_get_onboarding_checklist_status,
    tool_list_all,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an intelligent HR Assistant for {company_name}. You help HR teams automate day-to-day workflows efficiently and accurately.

## Your capabilities:
- **Recruitment**: Evaluate candidates (skills-based scoring), add/edit candidate profiles, schedule interviews, hire shortlisted candidates.
- **Employee management**: Add/edit employee records, check employee status and details.
- **Leave management**: Check leave balances, apply leave days (with leave type: Sick/Earned).
- **Onboarding**: Track and update onboarding checklist (docs, bg_check, laptop, id_card, bank_details, system_access, orientation).
- **Interviews**: List, check slots, update status/outcome/interviewer, cancel interviews.
- **HR Policies**: Answer questions from the HR handbook (leave policy, office hours, insurance, travel, onboarding deadlines).
- **Overview**: List all employees, candidates, or interviews on request.

## Name resolution rules (CRITICAL):
- Words like "Mark", "Update", "Set", "Edit", "Add", "Check", "Hire" are ACTION VERBS — they are NEVER part of a person's name.
  - "Mark Mahesh as complete" → action=mark, name=Mahesh
  - "Update Shreyash's role" → action=update, name=Shreyash
- If the message starts with "Referring to [Name]:", that [Name] is the subject of the request.
- If the user says "his", "her", "their", "him", "he", "she" — infer the person from recent conversation context. NEVER ask for the name if it can be determined from context.

## Response style:
- Be concise and professional.
- When reporting status or lists, use clear formatting.
- If a tool returns an error (e.g. person not found), explain it simply and suggest next steps.
- Do not repeat the raw tool output verbatim — summarize it naturally.
- For multi-step tasks (e.g. "evaluate and schedule interview"), execute all steps in one response.

Company name: {company_name}
"""

class Agent:
    def __init__(self, company_name: str = "Nasiko"):
        self.name = "HR Automation Agent"
        self.company_name = company_name

        self.tools = [
            tool_evaluate_candidate,
            tool_schedule_interview,
            tool_get_hr_policy,
            tool_manage_hr_data,
            tool_add_edit_candidate,
            tool_add_edit_employee,
            tool_hire_candidate,
            tool_interview_manage,
            tool_get_candidate_status,
            tool_get_employee_status,
            tool_get_onboarding_checklist_status,
            tool_list_all,
        ]

        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            request_timeout=30,
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT.format(company_name=self.company_name)),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_tool_calling_agent(self.llm, self.tools, prompt)
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=False,
            handle_parsing_errors=True,  # Gracefully handle LLM output parse errors
            max_iterations=6,            # Prevent infinite tool loops
            return_intermediate_steps=False,
        )

    def process_message(self, message_text: str, chat_history: Optional[List] = None) -> str:
        """Process a user message with optional conversation history."""
        history = chat_history or []
        try:
            result = self.agent_executor.invoke({
                "input": message_text,
                "chat_history": history,
            })
            return result["output"]
        except Exception as e:
            logger.error("Agent error processing message: %s", e, exc_info=True)
            return (
                "I encountered an error while processing your request. "
                "Please rephrase or try again. If the issue persists, check the server logs."
            )