from typing import List, Dict, Any, Optional
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
)

class Agent:
    def __init__(self):
        self.name = "HR Automation Agent"

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
        ]

        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are an HR Assistant. Use tools to: "
                "evaluate candidates (skills-based scoring); schedule interviews (check date AND time for collisions); "
                "add or edit candidates and employees; hire shortlisted candidates; "
                "manage leaves and onboarding (status, update); "
                "get onboarding checklist (document verification, laptop allocation, id card, bank details, system access, orientation); "
                "list/check/update interviews; get candidate or employee status; "
                "and retrieve HR policy from the handbook. "
                "IMPORTANT: When the user says 'Mark X as Y' or 'Update X' or 'Check X', the person's name is X. "
                "'Mark', 'Update', 'Check', 'Set', 'Edit' are action verbs, NOT part of the name. "
                "e.g. 'Mark Mahesh as complete' means name=Mahesh, NOT 'Mark Mahesh'. Company name is Nasiko. "
                "ALSO: Use conversation context. If the user says 'his status', 'her leaves', 'their onboarding' etc., "
                "refer to the person discussed in the previous messages (e.g. if they asked about Mahesh, 'his' means Mahesh)."
            ),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        agent = create_tool_calling_agent(self.llm, self.tools, prompt)
        self.agent_executor = AgentExecutor(agent=agent, tools=self.tools, verbose=False)
        
    def process_message(self, message_text: str, chat_history: Optional[List] = None) -> str:
        """Process message with optional conversation history for context (e.g. 'his' -> Mahesh)."""
        history = chat_history or []
        result = self.agent_executor.invoke({"input": message_text, "chat_history": history})
        return result["output"]