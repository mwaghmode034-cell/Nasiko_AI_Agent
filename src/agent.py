from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor, create_tool_calling_agent
# Use the new tool names
from tools import tool_evaluate_candidate, tool_schedule_interview, tool_get_hr_policy

class Agent:
    def __init__(self):
        self.name = "HR Automation Agent"
        self.tools = [tool_evaluate_candidate, tool_schedule_interview, tool_get_hr_policy]
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an HR Assistant. Use tools to evaluate candidates, schedule interviews, and check policies."),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        agent = create_tool_calling_agent(self.llm, self.tools, prompt)
        self.agent_executor = AgentExecutor(agent=agent, tools=self.tools, verbose=False)
        
    def process_message(self, message_text: str) -> str:
        result = self.agent_executor.invoke({"input": message_text})
        return result["output"]