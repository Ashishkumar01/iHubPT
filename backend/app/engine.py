from typing import Dict, Any, List, TypedDict, Annotated, Optional
from langgraph.graph import StateGraph
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.schema import BaseMessage
from .models import Agent, AgentStatus
from .tools import tool_registry
import chromadb
from datetime import datetime
import json
import os
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage, SystemMessage
from langchain.tools import Tool
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.schema.messages import AIMessage
from app.models import AgentCreate, AgentUpdate, ChatMessage
from app.vector_store import VectorStore
import logging

logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    messages: List[BaseMessage]
    current_step: str
    input: str
    tools: Dict[str, Any]

class AgentEngine:
    def __init__(self):
        self._active_agents: Dict[str, Dict[str, Any]] = {}
        self._initialize_db()
        self.vector_store = VectorStore()
        self.llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0.7,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.tool_registry = tool_registry

    def _initialize_db(self):
        """Initialize ChromaDB for agent storage."""
        persist_directory = os.path.join(os.path.dirname(__file__), "chroma_db")
        os.makedirs(persist_directory, exist_ok=True)
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection("agents")

    def _agent_to_dict(self, agent: Agent) -> Dict[str, Any]:
        """Convert an Agent object to a dictionary for storage."""
        try:
            return {
                "id": str(agent.id),  # Convert UUID to string
                "name": agent.name,
                "description": agent.description,
                "prompt": agent.prompt,
                "tools": json.dumps(agent.tools),  # Store tool names as JSON string
                "hitl_enabled": agent.hitl_enabled,
                "status": agent.status,
                "created_at": agent.created_at.isoformat(),
                "updated_at": agent.updated_at.isoformat()
            }
        except Exception as e:
            raise ValueError(f"Failed to convert agent to dictionary: {str(e)}")

    def _dict_to_agent(self, data: Dict[str, Any]) -> Agent:
        """Convert a dictionary to an Agent object."""
        try:
            # Convert datetime strings back to datetime objects
            data["created_at"] = datetime.fromisoformat(data["created_at"])
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
            
            # Convert tools string back to list of tool names
            data["tools"] = json.loads(data["tools"])
            
            return Agent(**data)
        except Exception as e:
            raise ValueError(f"Failed to convert dictionary to agent: {str(e)}")

    def create_agent(self, agent: Agent) -> Agent:
        """Create a new agent and store it in ChromaDB."""
        agent_dict = self._agent_to_dict(agent)
        self.collection.add(
            ids=[str(agent.id)],  # Convert UUID to string
            documents=[agent.description],
            metadatas=[agent_dict]
        )
        return agent

    def get_agents(self) -> List[Agent]:
        """Get all agents from ChromaDB."""
        results = self.collection.get()
        return [self._dict_to_agent(metadata) for metadata in results["metadatas"]]

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get a specific agent by ID from ChromaDB."""
        results = self.collection.get(ids=[str(agent_id)])  # Ensure ID is string
        if not results["ids"]:
            return None
        return self._dict_to_agent(results["metadatas"][0])

    def update_agent(self, agent_id: str, agent_update: Dict[str, Any]) -> Optional[Agent]:
        """Update an agent in ChromaDB."""
        agent = self.get_agent(agent_id)
        if not agent:
            return None
        
        # Update agent fields
        for key, value in agent_update.items():
            setattr(agent, key, value)
        agent.updated_at = datetime.utcnow()
        
        # Store updated agent
        agent_dict = self._agent_to_dict(agent)
        self.collection.update(
            ids=[agent_id],
            documents=[agent.description],
            metadatas=[agent_dict]
        )
        return agent

    def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent from ChromaDB."""
        try:
            self.collection.delete(ids=[agent_id])
            return True
        except Exception:
            return False

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

        # Add nodes for each tool name
        for tool_name in agent.tools:
            workflow.add_node(
                name=tool_name,
                func=lambda state, tool_name=tool_name: self._run_tool(state, tool_name)
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
        tool = self.tool_registry.get_tool(tool_name)
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

    async def process_chat_message(self, agent_id: str, message: str) -> str:
        """Process a chat message and return the agent's response."""
        try:
            # Get the agent from ChromaDB
            agent = self.get_agent(agent_id)
            if not agent:
                raise ValueError(f"Agent {agent_id} not found")

            # Create the system message with agent's prompt
            system_message = SystemMessage(content=agent.prompt)
            
            # Create the human message
            human_message = HumanMessage(content=message)
            
            # Get the chat history from the agent's context
            chat_history = agent.context.get("chat_history", [])
            
            # Create messages list with history
            messages = [system_message] + chat_history + [human_message]
            
            # Get response from the LLM
            response = await self.llm.ainvoke(messages)
            
            # Update chat history
            chat_history.extend([human_message, response])
            agent.context["chat_history"] = chat_history
            
            # Update the agent in ChromaDB
            self.update_agent(agent_id, {"context": agent.context})
            
            return response.content
            
        except Exception as e:
            logger.error(f"Error processing chat message: {str(e)}")
            raise

# Create a global engine instance
agent_engine = AgentEngine() 