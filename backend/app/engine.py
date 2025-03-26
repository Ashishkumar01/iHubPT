from typing import Dict, Any, List, TypedDict, Annotated
from langgraph.graph import StateGraph
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.schema import BaseMessage
from .models import Agent, AgentStatus
from .tools import tool_registry

class AgentState(TypedDict):
    messages: List[BaseMessage]
    current_step: str
    input: str
    tools: Dict[str, Any]

class AgentEngine:
    def __init__(self):
        self._active_agents: Dict[str, Dict[str, Any]] = {}

    def create_workflow(self, agent: Agent) -> StateGraph:
        """Create a LangGraph workflow for the agent."""
        # Create the base prompt template
        prompt = PromptTemplate(
            input_variables=["input", "tools", "messages"],
            template=agent.prompt
        )

        # Create the LLM chain
        chain = LLMChain(
            llm=agent.llm,  # You'll need to set this up
            prompt=prompt
        )

        # Create the graph
        workflow = StateGraph(AgentState)

        # Add nodes for each tool
        for tool in agent.tools:
            workflow.add_node(
                name=tool.name,
                func=lambda state, tool_name=tool.name: self._run_tool(state, tool_name)
            )

        # Add the main chain node
        workflow.add_node(
            name="main",
            func=lambda state: self._run_chain(state, chain)
        )

        # Define edges and conditions
        workflow.add_edge("main", "tools")
        workflow.add_edge("tools", "main")

        # Set the entry point
        workflow.set_entry_point("main")

        return workflow

    def _run_tool(self, state: AgentState, tool_name: str) -> AgentState:
        """Run a tool and update the state."""
        tool = tool_registry.get_tool(tool_name)
        result = tool.run(state["input"])
        
        # Update state with tool result
        state["messages"].append(BaseMessage(content=f"Tool {tool_name} result: {result}"))
        state["current_step"] = "main"
        return state

    def _run_chain(self, state: AgentState, chain: LLMChain) -> AgentState:
        """Run the LLM chain and update the state."""
        result = chain.run(
            input=state["input"],
            tools=state["tools"],
            messages=state["messages"]
        )
        
        # Update state with chain result
        state["messages"].append(BaseMessage(content=result))
        state["current_step"] = "tools"
        return state

    def start_agent(self, agent: Agent) -> str:
        """Start an agent's workflow."""
        if agent.id in self._active_agents:
            raise ValueError(f"Agent {agent.id} is already running")

        workflow = self.create_workflow(agent)
        self._active_agents[agent.id] = {
            "workflow": workflow,
            "status": AgentStatus.RUNNING,
            "current_step": None
        }
        return agent.id

    def pause_agent(self, agent_id: str) -> None:
        """Pause an agent's workflow."""
        if agent_id not in self._active_agents:
            raise ValueError(f"Agent {agent_id} not found")
        
        self._active_agents[agent_id]["status"] = AgentStatus.PAUSED

    def resume_agent(self, agent_id: str) -> None:
        """Resume a paused agent's workflow."""
        if agent_id not in self._active_agents:
            raise ValueError(f"Agent {agent_id} not found")
        
        if self._active_agents[agent_id]["status"] != AgentStatus.PAUSED:
            raise ValueError(f"Agent {agent_id} is not paused")
        
        self._active_agents[agent_id]["status"] = AgentStatus.RUNNING

    def get_agent_status(self, agent_id: str) -> AgentStatus:
        """Get the current status of an agent."""
        if agent_id not in self._active_agents:
            raise ValueError(f"Agent {agent_id} not found")
        
        return self._active_agents[agent_id]["status"]

# Create a global engine instance
agent_engine = AgentEngine() 