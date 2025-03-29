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
from app.config import Settings
import logging
import time
from langchain.callbacks import get_openai_callback

logger = logging.getLogger(__name__)

# Load settings
settings = Settings()

class AgentState(TypedDict):
    messages: List[BaseMessage]
    current_step: str
    input: str
    tools: Dict[str, Any]

class TokenUsageCallback:
    def __init__(self):
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
        self.total_cost = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> None:
        """Run when LLM starts running."""
        pass

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        """Run when LLM ends running."""
        if hasattr(response, 'usage'):
            self.prompt_tokens = response.usage.prompt_tokens
            self.completion_tokens = response.usage.completion_tokens
            self.total_tokens = response.usage.total_tokens
            self.total_cost = response.usage.total_cost

    def on_llm_error(self, error: Exception, **kwargs: Any) -> None:
        """Run when LLM errors."""
        logger.error(f"LLM error: {error}")

class AgentEngine:
    def __init__(self):
        self._active_agents: Dict[str, Dict[str, Any]] = {}
        self._initialize_db()
        self.vector_store = VectorStore()
        
        # Initialize LLM with settings
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
            
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=settings.OPENAI_TEMPERATURE,
            max_tokens=settings.OPENAI_MAX_TOKENS,
            api_key=api_key
        )
        logger.info(f"Initialized LLM with model: {settings.OPENAI_MODEL}")
        
        self.tool_registry = tool_registry

    def _initialize_db(self):
        """Initialize ChromaDB for agent storage."""
        try:
            persist_directory = os.path.join(os.path.dirname(__file__), "chroma_db")
            os.makedirs(persist_directory, exist_ok=True)
            
            # Initialize ChromaDB client with logging
            logger.info(f"Initializing ChromaDB with persist directory: {persist_directory}")
            self.client = chromadb.PersistentClient(path=persist_directory)
            
            # Create or get collection with explicit schema
            self.collection = self.client.get_or_create_collection(
                name="agents",
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("ChromaDB collection 'agents' initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {str(e)}")
            raise

    def _agent_to_dict(self, agent: Agent) -> Dict[str, Any]:
        """Convert an Agent object to a dictionary for storage."""
        try:
            agent_dict = {
                "id": str(agent.id),
                "name": agent.name,
                "description": agent.description,
                "prompt": agent.prompt,
                "tools": json.dumps(agent.tools),
                "hitl_enabled": str(agent.hitl_enabled).lower(),  # Store as string
                "status": agent.status.value.upper(),  # Store enum value in uppercase
                "created_at": agent.created_at.isoformat(),
                "updated_at": agent.updated_at.isoformat()
            }
            logger.debug(f"Converted agent to dict: {agent_dict}")
            return agent_dict
        except Exception as e:
            logger.error(f"Failed to convert agent to dictionary: {str(e)}")
            raise ValueError(f"Failed to convert agent to dictionary: {str(e)}")

    def _dict_to_agent(self, data: Dict[str, Any]) -> Agent:
        """Convert a dictionary to an Agent object."""
        try:
            # Convert string values back to appropriate types
            agent_data = {
                "id": data["id"],
                "name": data["name"],
                "description": data["description"],
                "prompt": data["prompt"],
                "tools": json.loads(data["tools"]),
                "hitl_enabled": data["hitl_enabled"] == "true",
                "status": AgentStatus(data["status"].upper()),  # Convert to uppercase before creating enum
                "created_at": datetime.fromisoformat(data["created_at"]),
                "updated_at": datetime.fromisoformat(data["updated_at"])
            }
            logger.debug(f"Converting dict to agent: {agent_data}")
            return Agent(**agent_data)
        except Exception as e:
            logger.error(f"Failed to convert dictionary to agent: {str(e)}")
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
        try:
            results = self.collection.get()
            if not results["metadatas"]:
                logger.info("No agents found in collection")
                return []
            
            agents = []
            for metadata in results["metadatas"]:
                try:
                    agent = self._dict_to_agent(metadata)
                    agents.append(agent)
                except Exception as e:
                    logger.error(f"Failed to convert agent metadata: {str(e)}")
                    continue
            
            logger.info(f"Successfully retrieved {len(agents)} agents")
            return agents
            
        except Exception as e:
            logger.error(f"Error retrieving agents: {str(e)}")
            raise

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
        
        try:
            # Update agent fields
            if "name" in agent_update:
                agent.name = agent_update["name"]
            if "description" in agent_update:
                agent.description = agent_update["description"]
            if "prompt" in agent_update:
                agent.prompt = agent_update["prompt"]
            if "tools" in agent_update:
                agent.tools = agent_update["tools"]
            if "hitl_enabled" in agent_update:
                agent.hitl_enabled = bool(agent_update["hitl_enabled"])
            if "status" in agent_update:
                agent.status = agent_update["status"]
            
            agent.updated_at = datetime.utcnow()
            
            # Store updated agent
            agent_dict = self._agent_to_dict(agent)
            self.collection.update(
                ids=[agent_id],
                documents=[agent.description],
                metadatas=[agent_dict]
            )
            
            logger.info(f"Successfully updated agent {agent_id}")
            return agent
            
        except Exception as e:
            logger.error(f"Failed to update agent {agent_id}: {str(e)}")
            raise ValueError(f"Failed to update agent: {str(e)}")

    def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent and clean up its resources."""
        agent_id = str(agent_id)
        try:
            # Clean up active agent if running
            if agent_id in self._active_agents:
                self.pause_agent(agent_id)
                del self._active_agents[agent_id]
            
            # Delete from database
            self.collection.delete(ids=[agent_id])
            
            logger.info(f"Agent {agent_id} deleted successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to delete agent {agent_id}: {str(e)}")
            return False

    def create_workflow(self, agent: Agent) -> StateGraph:
        """Create a LangGraph workflow for the agent."""
        try:
            # Create the base prompt template with agent's prompt
            prompt = ChatPromptTemplate.from_messages([
                ("system", agent.prompt),
                ("human", "{input}")
            ])

            # Create the chain using the new RunnableSequence pattern
            chain = prompt | self.llm

            # Create the graph
            workflow = StateGraph(AgentState)

            # Initialize the state
            initial_state = {
                "messages": [],
                "current_step": "main",
                "input": "",
                "tools": {}
            }

            # Add nodes for each tool
            available_tools = {}
            for tool_name in agent.tools:
                try:
                    tool = self.tool_registry.get_tool(tool_name)
                    available_tools[tool_name] = tool
                    workflow.add_node(
                        tool_name,
                        lambda state, t=tool: self._run_tool(state, t)
                    )
                except ValueError as e:
                    logger.warning(f"Tool {tool_name} not found: {str(e)}")

            # Add the main chain node
            workflow.add_node(
                "main",
                lambda state: self._run_chain(state, chain)
            )

            return workflow

        except Exception as e:
            logger.error(f"Error creating workflow: {str(e)}")
            raise ValueError(f"Failed to create workflow: {str(e)}")

    def _run_tool(self, state: AgentState, tool: Tool) -> AgentState:
        """Run a tool and update the state."""
        try:
            result = tool.run(state["input"])
            
            # Update state with tool result
            state["messages"].append(AIMessage(content=f"Tool result: {result}"))
            state["current_step"] = "main"
            return state
        except Exception as e:
            logger.error(f"Error running tool: {str(e)}")
            state["messages"].append(AIMessage(content=f"Error running tool: {str(e)}"))
            state["current_step"] = "main"
            return state

    def _run_chain(self, state: AgentState, chain) -> AgentState:
        """Run the chain and update the state."""
        try:
            # Prepare the input for the chain
            chain_input = {
                "input": state["input"],
                "chat_history": "\n".join([msg.content for msg in state["messages"]])
            }
            
            # Run the chain
            result = chain.invoke(chain_input)
            
            # Update state with chain result
            state["messages"].append(AIMessage(content=result.content))
            state["current_step"] = "main"
            return state
        except Exception as e:
            logger.error(f"Error running chain: {str(e)}")
            state["messages"].append(AIMessage(content=f"Error: {str(e)}"))
            state["current_step"] = "main"
            return state

    def start_agent(self, agent: Agent) -> None:
        """Start an agent's workflow."""
        agent_id = str(agent.id)
        if agent_id in self._active_agents:
            raise ValueError(f"Agent {agent_id} is already running")

        try:
            # Create and initialize the workflow
            workflow = self.create_workflow(agent)
            
            # Initialize the agent state
            initial_state = {
                "messages": [],
                "current_step": "main",
                "input": "",
                "tools": {
                    name: self.tool_registry.get_tool(name)
                    for name in agent.tools
                }
            }
            
            # Store the active agent
            self._active_agents[agent_id] = {
                "workflow": workflow,
                "state": initial_state,
                "status": AgentStatus.RUNNING,
                "agent": agent
            }
            
            logger.info(f"Agent {agent_id} started successfully")
            
            # Update agent status in database
            self.update_agent(agent_id, {"status": AgentStatus.RUNNING})
            
        except Exception as e:
            logger.error(f"Failed to start agent {agent_id}: {str(e)}")
            # Update agent status to failed in database
            self.update_agent(agent_id, {"status": AgentStatus.FAILED})
            raise ValueError(f"Failed to start agent: {str(e)}")

    def pause_agent(self, agent_id: str) -> None:
        """Pause a running agent."""
        agent_id = str(agent_id)
        if agent_id not in self._active_agents:
            raise ValueError(f"Agent {agent_id} is not running")

        try:
            # Store current state and pause workflow
            agent_state = self._active_agents[agent_id]
            agent_state["status"] = AgentStatus.PAUSED
            
            logger.info(f"Agent {agent_id} paused successfully")
        except Exception as e:
            logger.error(f"Failed to pause agent {agent_id}: {str(e)}")
            raise ValueError(f"Failed to pause agent: {str(e)}")

    def resume_agent(self, agent_id: str) -> None:
        """Resume a paused agent."""
        agent_id = str(agent_id)
        if agent_id not in self._active_agents:
            raise ValueError(f"Agent {agent_id} is not active")

        agent_state = self._active_agents[agent_id]
        if agent_state["status"] != AgentStatus.PAUSED:
            raise ValueError(f"Agent {agent_id} is not paused")

        try:
            # Resume the workflow
            agent_state["status"] = AgentStatus.RUNNING
            
            logger.info(f"Agent {agent_id} resumed successfully")
        except Exception as e:
            logger.error(f"Failed to resume agent {agent_id}: {str(e)}")
            raise ValueError(f"Failed to resume agent: {str(e)}")

    def get_agent_status(self, agent_id: str) -> AgentStatus:
        """Get the current status of an agent."""
        agent_id = str(agent_id)
        # First check active agents
        if agent_id in self._active_agents:
            return self._active_agents[agent_id]["status"]
        
        # If not active, get from database
        agent = self.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        return agent.status

    async def process_chat_message(self, agent_id: str, message: str, requestor_id: str = "administrator") -> str:
        """Process a chat message and return the response."""
        start_time = time.time()
        token_callback = TokenUsageCallback()
        
        try:
            # Get the agent (synchronous operation)
            agent = self.get_agent(agent_id)
            if not agent:
                raise ValueError(f"Agent {agent_id} not found")

            # Create messages for the conversation
            system_message = SystemMessage(content=agent.prompt)
            human_message = HumanMessage(content=message)

            # Compile chat history
            messages = [system_message]
            if hasattr(agent, 'context') and agent.context and agent.context.get("chat_history"):
                messages.extend(agent.context["chat_history"])
            messages.append(human_message)

            # Get response from language model (async operation) with token tracking
            with get_openai_callback() as cb:
                response = await self.llm.ainvoke(messages)
                token_callback.prompt_tokens = cb.prompt_tokens
                token_callback.completion_tokens = cb.completion_tokens
                token_callback.total_tokens = cb.total_tokens
                token_callback.total_cost = cb.total_cost

            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)

            # Create chat log entry with flattened metadata
            chat_log_data = {
                "agent_id": agent_id,
                "request_message": message,
                "response_message": response.content,
                "input_tokens": token_callback.prompt_tokens,
                "output_tokens": token_callback.completion_tokens,
                "total_tokens": token_callback.total_tokens,
                "requestor_id": requestor_id,
                "model_name": self.llm.model_name,
                "duration_ms": duration_ms,
                "status": "success",
                "temperature": str(self.llm.temperature),
                "max_tokens": str(self.llm.max_tokens) if self.llm.max_tokens else "None",
                "cost": token_callback.total_cost
            }

            # Log the chat interaction (synchronous operation)
            self.vector_store.add_chat_log(chat_log_data)

            # Update agent context
            context = getattr(agent, 'context', {}) or {}
            if "chat_history" not in context:
                context["chat_history"] = []
            context["chat_history"].append(human_message)
            context["chat_history"].append(response)

            # Update agent in database (synchronous operation)
            self.update_agent(agent_id, {"context": context})

            return response.content

        except Exception as e:
            # Log error in chat log with flattened structure
            duration_ms = int((time.time() - start_time) * 1000)
            error_log_data = {
                "agent_id": agent_id,
                "request_message": message,
                "response_message": "",
                "input_tokens": token_callback.prompt_tokens,
                "output_tokens": token_callback.completion_tokens,
                "total_tokens": token_callback.total_tokens,
                "requestor_id": requestor_id,
                "model_name": self.llm.model_name,
                "duration_ms": duration_ms,
                "status": "error",
                "error_message": str(e),
                "temperature": str(self.llm.temperature),
                "max_tokens": str(self.llm.max_tokens) if self.llm.max_tokens else "None",
                "cost": token_callback.total_cost
            }
            self.vector_store.add_chat_log(error_log_data)
            
            logger.error(f"Error processing chat message: {str(e)}")
            raise

# Create a global engine instance
agent_engine = AgentEngine() 