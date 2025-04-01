from typing import Dict, Any, List, TypedDict, Annotated, Optional, Tuple
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
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain.tools import Tool
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.agents import AgentFinish
from langchain_core.messages import FunctionMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationSummaryBufferMemory
from app.models import AgentCreate, AgentUpdate, ChatMessage
from app.vector_store import VectorStore
from app.config import Settings
import logging
import time
from langchain.callbacks import get_openai_callback
import uuid

logger = logging.getLogger(__name__)

# Load settings
settings = Settings()

# Set tokenizers parallelism before initializing memory
os.environ["TOKENIZERS_PARALLELISM"] = "false"

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
        self.total_cost = 0.0

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
            usage = response.usage
            self.prompt_tokens += getattr(usage, 'prompt_tokens', 0)
            self.completion_tokens += getattr(usage, 'completion_tokens', 0)
            self.total_tokens += getattr(usage, 'total_tokens', 0)
            self.total_cost += getattr(usage, 'total_cost', 0.0)
        # Handle different response types
        elif isinstance(response, dict) and 'usage' in response:
            usage = response['usage']
            self.prompt_tokens += usage.get('prompt_tokens', 0)
            self.completion_tokens += usage.get('completion_tokens', 0)
            self.total_tokens += usage.get('total_tokens', 0)
            self.total_cost += usage.get('total_cost', 0.0)

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
            
            # Create chat logs collection
            self.chat_logs = self.client.get_or_create_collection(
                name="chat_logs",
                metadata={"hnsw:space": "cosine"}
            )
            
            logger.info("ChromaDB collections initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {str(e)}")
            raise

    def _serialize_metadata(self, data: Dict[str, Any]) -> Dict[str, str]:
        """
        Ensure all metadata values are strings for ChromaDB.
        
        Args:
            data (Dict[str, Any]): The data dictionary with potentially non-string values
            
        Returns:
            Dict[str, str]: The data dictionary with all values as strings
        """
        serialized = {}
        for key, value in data.items():
            # Handle numeric values carefully
            if key in ['input_tokens', 'output_tokens', 'total_tokens']:
                try:
                    # Convert to int first to ensure it's a valid number, then to string
                    serialized[key] = str(int(value))
                except (ValueError, TypeError):
                    serialized[key] = '0'
            elif key == 'cost':
                try:
                    # Format cost with proper precision
                    serialized[key] = str(float(value))
                except (ValueError, TypeError):
                    serialized[key] = '0.0'
            elif key == 'duration_ms':
                try:
                    serialized[key] = str(int(value))
                except (ValueError, TypeError):
                    serialized[key] = '0'
            else:
                # For all other values, just convert to string
                serialized[key] = str(value) if value is not None else ""
                
        return serialized

    def _agent_to_dict(self, agent: Agent) -> Dict[str, Any]:
        """Convert an Agent object to a dictionary for storage."""
        try:
            agent_dict = {
                "id": str(agent.id),
                "name": agent.name,
                "description": agent.description,
                "prompt": agent.prompt,
                "tools": json.dumps(agent.tools),
                "hitl_enabled": str(agent.hitl_enabled).lower(),
                "status": agent.status.value.upper(),
                "created_at": agent.created_at.isoformat(),
                "updated_at": agent.updated_at.isoformat(),
                "context": json.dumps(agent.context) if hasattr(agent, 'context') and agent.context else "{}"
            }
            # Ensure all values are strings
            agent_dict = self._serialize_metadata(agent_dict)
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
                "status": AgentStatus(data["status"].upper()),
                "created_at": datetime.fromisoformat(data["created_at"]),
                "updated_at": datetime.fromisoformat(data["updated_at"]),
                "context": json.loads(data.get("context", "{}"))
            }
            logger.debug(f"Converting dict to agent: {agent_data}")
            return Agent(**agent_data)
        except Exception as e:
            logger.error(f"Failed to convert dictionary to agent: {str(e)}")
            raise ValueError(f"Failed to convert dictionary to agent: {str(e)}")

    def create_agent(self, agent: Agent) -> Agent:
        """Create a new agent and store it in ChromaDB."""
        # Initialize context if not present
        if not hasattr(agent, 'context') or not agent.context:
            agent.context = {
                "chat_history": [],
                "created_at": datetime.utcnow().isoformat()
            }
        
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
            system_template = agent.prompt
            
            # Ensure tool information is included if needed
            if "agent_scratchpad" not in system_template and "tool" in system_template.lower():
                # Add minimal instructions for tool usage if needed
                system_template += "\n\nYou have access to the following tools:\n"
                tools = []
                for tool_name in agent.tools:
                    try:
                        tool = self.tool_registry.get_tool(tool_name)
                        tools.append(tool)
                        system_template += f"\n- {tool.name}: {tool.description}"
                    except ValueError as e:
                        logger.warning(f"Tool {tool_name} not found: {str(e)}")

            # Create the prompt template
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_template),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
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
        
        if agent_id in self._active_agents:
            # Agent is actively running in memory
            try:
                agent_state = self._active_agents[agent_id]
                if agent_state["status"] == AgentStatus.RUNNING:
                    agent_state["status"] = AgentStatus.PAUSED
                    logger.info(f"Agent {agent_id} paused in memory")
                    # Note: DB status is updated by the endpoint after this call succeeds
                else:
                    logger.warning(f"Agent {agent_id} is in active list but not RUNNING (Status: {agent_state['status']}). Cannot pause.")
                    # Optionally raise an error here if this state is unexpected
            except Exception as e:
                logger.error(f"Error pausing agent {agent_id} in memory: {str(e)}")
                raise ValueError(f"Failed to pause agent {agent_id}: {str(e)}")
        else:
            # Agent is not in the active memory dictionary (possibly due to restart)
            # Check the database status
            logger.warning(f"Agent {agent_id} not found in active agents list. Checking database status.")
            agent = self.get_agent(agent_id)
            if not agent:
                raise ValueError(f"Agent {agent_id} not found in database")

            if agent.status == AgentStatus.RUNNING:
                # If DB says running, update DB status directly to PAUSED
                logger.info(f"Agent {agent_id} found running in DB but not active. Setting status to PAUSED in DB.")
                self.update_agent(agent_id, {"status": AgentStatus.PAUSED})
            elif agent.status == AgentStatus.PAUSED:
                logger.info(f"Agent {agent_id} is already PAUSED in the database.")
            else:
                # Agent exists but is IDLE in DB, cannot pause
                logger.warning(f"Agent {agent_id} found in DB but status is {agent.status}. Cannot pause.")
                raise ValueError(f"Agent {agent_id} is not running (status: {agent.status})")

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

    def get_chat_logs(self, start_time: str = None, end_time: str = None, agent_id: str = None) -> List[Dict[str, Any]]:
        """Get chat logs within a time range and/or for a specific agent."""
        try:
            # Build the where clause
            where_clause = {}
            if start_time and end_time:
                where_clause["timestamp"] = {"$gte": start_time, "$lte": end_time}
            if agent_id:
                where_clause["agent_id"] = str(agent_id)

            # Query the chat logs collection
            results = self.chat_logs.get(
                where=where_clause if where_clause else None
            )

            # Convert results to list of dictionaries with all required fields
            chat_logs = []
            for idx, metadata in enumerate(results["metadatas"]):
                # Ensure we have a valid ID
                log_id = results["ids"][idx] if idx < len(results["ids"]) else str(uuid.uuid4())
                
                chat_log = {
                    "id": log_id,  # Ensure id is present and valid
                    "content": results["documents"][idx] if idx < len(results["documents"]) else "",
                    "agent_id": metadata.get("agent_id", ""),
                    "request_message": metadata.get("request_message", ""),
                    "response_message": metadata.get("response_message", ""),
                    "input_tokens": int(metadata.get("input_tokens", "0")),
                    "output_tokens": int(metadata.get("output_tokens", "0")),
                    "total_tokens": int(metadata.get("total_tokens", "0")),
                    "requestor_id": metadata.get("requestor_id", ""),
                    "model_name": metadata.get("model_name", ""),
                    "duration_ms": int(metadata.get("duration_ms", "0")),
                    "status": metadata.get("status", "unknown"),
                    "temperature": float(metadata.get("temperature", "0")),
                    "max_tokens": metadata.get("max_tokens", "none"),
                    "cost": float(metadata.get("cost", "0")),
                    "timestamp": metadata.get("timestamp", ""),
                    "tool_calls": metadata.get("tool_calls", "[]"),
                    "has_tool_calls": metadata.get("has_tool_calls", "false"),
                    "memory_summary": metadata.get("memory_summary", ""),
                    "has_memory": metadata.get("has_memory", "false"),
                    "error_message": metadata.get("error_message", ""),
                    "user": metadata.get("requestor_id", "Administrator"),  # Map requestor_id to user
                    "department": "Post Trade"  # Default department
                }
                chat_logs.append(chat_log)

            return chat_logs

        except Exception as e:
            logger.error(f"Error retrieving chat logs: {str(e)}")
            raise

    def add_chat_log(self, chat_log_data: Dict[str, Any]) -> None:
        """Add a chat log entry to ChromaDB."""
        try:
            # Ensure all metadata values are strings
            metadata = self._serialize_metadata(chat_log_data)
            
            # Explicitly convert token counts and cost to strings
            if "input_tokens" in metadata and not isinstance(metadata["input_tokens"], str):
                metadata["input_tokens"] = str(metadata["input_tokens"])
            if "output_tokens" in metadata and not isinstance(metadata["output_tokens"], str):
                metadata["output_tokens"] = str(metadata["output_tokens"])
            if "total_tokens" in metadata and not isinstance(metadata["total_tokens"], str):
                metadata["total_tokens"] = str(metadata["total_tokens"])
            if "cost" in metadata and not isinstance(metadata["cost"], str):
                metadata["cost"] = str(metadata["cost"])
            
            # Add to chat logs collection
            self.chat_logs.add(
                ids=[str(uuid.uuid4())],
                documents=[metadata["response_message"]],
                metadatas=[metadata]
            )
            
        except Exception as e:
            logger.error(f"Failed to save chat log: {str(e)}")
            logger.error(f"Chat log data: {json.dumps(chat_log_data)}")
            raise

    async def process_chat_message(self, agent_id: str, message: str, requestor_id: str = "administrator") -> str:
        """Process a chat message and return the response."""
        start_time = time.time()
        token_callback = TokenUsageCallback()
        
        try:
            # Get the agent
            agent = self.get_agent(agent_id)
            if not agent:
                raise ValueError(f"Agent {agent_id} not found")

            # Get the tools for this agent
            tools = []
            for tool_name in agent.tools:
                try:
                    tool = self.tool_registry.get_tool(tool_name)
                    tools.append(tool)
                except ValueError as e:
                    logger.warning(f"Tool {tool_name} not found: {str(e)}")

            # Initialize memory with the engine's LLM for summarization
            memory = ConversationSummaryBufferMemory(
                llm=self.llm,  # Use the engine's LLM instance
                max_token_limit=16000,  # Increased token limit for more context
                memory_key="chat_history",
                return_messages=True,
                output_key="output",
                moving_summary_buffer="",  # Start with empty summary to maximize recent messages
                human_prefix="User",  # Clearer role labels
                ai_prefix="Assistant"  # Clearer role labels
            )
            
            # Load existing conversation history if available
            if agent.context:
                try:
                    # Parse the JSON context
                    context = json.loads(agent.context)
                    
                    # Get the conversation history
                    if "chat_history" in context:
                        messages_to_load = context["chat_history"]
                        logger.info(f"Loading {len(messages_to_load)} messages from agent context")
                        
                        for msg in messages_to_load:
                            if msg["role"] == "user":
                                memory.chat_memory.add_message(HumanMessage(content=msg["content"]))
                            elif msg["role"] == "assistant":
                                memory.chat_memory.add_message(AIMessage(content=msg["content"]))
                            elif msg["role"] == "function":
                                memory.chat_memory.add_message(FunctionMessage(
                                    content=msg["content"],
                                    name=msg.get("name", "unknown_function")
                                ))
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse agent context: {str(e)}")
                except Exception as e:
                    logger.error(f"Error loading chat history: {str(e)}")
                    
                # Log the number of messages loaded into memory
                logger.info(f"Memory now contains {len(memory.chat_memory.messages)} messages after loading")
            
            # Add the current message to memory
            memory.chat_memory.add_message(HumanMessage(content=message))
            
            # Add task reminder about previous instructions if relevant
            # Scan the chat history for important tasks
            important_keywords = ["create label", "mark", "label", "priority", "high_priority"]
            recent_requests = []
            
            # Find the last 5 messages from the user for context
            user_messages = [msg for msg in memory.chat_memory.messages if isinstance(msg, HumanMessage)][-5:]
            
            # Check for any important tasks in recent user messages
            for msg in user_messages:
                if any(keyword in msg.content.lower() for keyword in important_keywords):
                    recent_requests.append(msg.content)
            
            # If we found important requests, add a reminder
            if recent_requests:
                # Add a system message at the beginning reminding of these important requests
                reminder = "IMPORTANT CONTEXT - Previous requests to remember:\n"
                for req in recent_requests:
                    reminder += f"- {req}\n"
                
                # Insert this reminder as a system message at the start of chat history
                memory.chat_memory.messages.insert(0, SystemMessage(content=reminder))
                logger.info(f"Added context reminder: {reminder[:100]}...")

            # Create the system message using the agent's configured prompt
            system_template = agent.prompt
            
            # Add specific instructions for email handling to preserve message IDs
            email_instructions = """
CRITICAL INSTRUCTIONS FOR EMAIL HANDLING:
1. When displaying email information from the gmail_unread tool, ALWAYS include the Message ID for each email
2. NEVER reformat or hide message IDs - they are required for taking actions on emails
3. Display the Message ID on a separate line for each email to make it clearly visible
4. When suggesting actions, mention that users need to provide the message ID for those actions
5. Present the full, unmodified output of email tools to maintain all necessary information
"""
            
            # Add email instructions to the prompt
            if "gmail" in " ".join(agent.tools):
                if not any(email_keyword in system_template.lower() for email_keyword in ["email", "gmail"]):
                    system_template += "\n\n" + email_instructions
                elif "message id" not in system_template.lower():
                    system_template += "\n\n" + email_instructions
            
            # Ensure critical instruction for tool usage is included
            if "agent_scratchpad" not in system_template and "tool" in system_template.lower():
                # Add minimal instructions for tool usage if needed
                system_template += "\n\nYou have access to the following tools:\n"
                for tool in tools:
                    system_template += f"\n- {tool.name}: {tool.description}"
            
            # Create the prompt template with chat history and agent_scratchpad
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_template),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ])
            
            # Bind the LLM with tool specifications for function calling
            llm_with_tools = self.llm.bind(
                functions=[{
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.args_schema.schema() if tool.args_schema else {}
                } for tool in tools]
            )
            
            agent = create_openai_functions_agent(
                llm=llm_with_tools,
                tools=tools,
                prompt=prompt
            )
            
            # Create the agent executor with memory
            agent_executor = AgentExecutor(
                agent=agent,
                tools=tools,
                memory=memory,
                verbose=True,
                handle_parsing_errors=True,
                max_iterations=5,  # Prevent infinite loops
                return_intermediate_steps=True  # This helps with tracking tool usage
            )

            # Execute the agent with token tracking
            with get_openai_callback() as cb:
                # Make sure we're retaining immediate context by grabbing most recent messages
                recent_exchange = []
                for msg in memory.chat_memory.messages[-4:]:  # Get last 4 messages (2 turns of conversation)
                    if isinstance(msg, HumanMessage):
                        recent_exchange.append(("human", msg.content))
                    elif isinstance(msg, AIMessage):
                        recent_exchange.append(("ai", msg.content))
                
                # If we have a recent exchange, log it for debugging
                if recent_exchange:
                    context_summary = " → ".join([f"{role}: {content[:30]}..." for role, content in recent_exchange])
                    logger.info(f"Recent conversation context: {context_summary}")
                
                # Execute agent with the properly formatted context
                response = await agent_executor.ainvoke(
                    {
                        "input": message,
                    }
                )
                
                # Update token tracking from the callback
                token_callback.prompt_tokens = cb.prompt_tokens
                token_callback.completion_tokens = cb.completion_tokens
                token_callback.total_tokens = cb.total_tokens
                token_callback.total_cost = cb.total_cost

            # Get the final output
            output = response["output"]

            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)

            # Log token usage information
            logger.info(f"Token usage - Prompt: {token_callback.prompt_tokens}, " +
                       f"Completion: {token_callback.completion_tokens}, " +
                       f"Total: {token_callback.total_tokens}")
            logger.info(f"Estimated cost: ${token_callback.total_cost:.6f}")

            # Create chat log entry with primitive types only and ensure everything is a string
            chat_log_data = {
                "agent_id": str(agent_id),
                "request_message": str(message),
                "response_message": str(output),
                "input_tokens": str(token_callback.prompt_tokens),
                "output_tokens": str(token_callback.completion_tokens),
                "total_tokens": str(token_callback.total_tokens),
                "requestor_id": str(requestor_id),
                "model_name": str(self.llm.model_name),
                "duration_ms": str(duration_ms),
                "status": "success",
                "temperature": str(self.llm.temperature),
                "max_tokens": str(self.llm.max_tokens) if self.llm.max_tokens else "none",
                "cost": str(token_callback.total_cost),
                "timestamp": datetime.utcnow().isoformat()
            }

            # Make sure to log the token information
            logger.info(f"Prompt tokens: {token_callback.prompt_tokens}")
            logger.info(f"Completion tokens: {token_callback.completion_tokens}")
            logger.info(f"Total tokens: {token_callback.total_tokens}")
            logger.info(f"Estimated cost: ${token_callback.total_cost:.4f}")

            # Add tool calls and memory info as serialized strings
            if response.get("intermediate_steps"):
                tool_calls = []
                for step in response.get("intermediate_steps", []):
                    if isinstance(step, tuple) and len(step) == 2:
                        try:
                            tool_call = {
                                "tool": str(step[0].tool) if hasattr(step[0], 'tool') else "unknown",
                                "tool_input": str(step[0].tool_input) if hasattr(step[0], 'tool_input') else "",
                                "tool_output": str(step[1])
                            }
                            tool_calls.append(tool_call)
                        except Exception as e:
                            logger.error(f"Error serializing tool call: {str(e)}")
                            # Add a simplified version if serialization fails
                            tool_calls.append({
                                "tool": "unknown",
                                "tool_input": "error serializing input",
                                "tool_output": "error serializing output"
                            })
                chat_log_data["tool_calls"] = json.dumps(tool_calls)
                chat_log_data["has_tool_calls"] = "true"
            else:
                chat_log_data["tool_calls"] = "[]"
                chat_log_data["has_tool_calls"] = "false"

            # Add memory summary as a string
            if memory.moving_summary_buffer:
                chat_log_data["memory_summary"] = str(memory.moving_summary_buffer)
                chat_log_data["has_memory"] = "true"
            else:
                chat_log_data["memory_summary"] = ""
                chat_log_data["has_memory"] = "false"

            # Ensure all metadata values are strings
            chat_log_data = self._serialize_metadata(chat_log_data)

            # Create and save chat log
            try:
                self.add_chat_log(chat_log_data)
            except Exception as e:
                logger.error(f"Failed to save chat log: {str(e)}")
                # Continue execution even if logging fails

            # Convert messages to serializable format and update agent context
            try:
                # Get current agent to update
                current_agent = self.get_agent(agent_id)
                if not current_agent:
                    raise ValueError(f"Agent {agent_id} not found")
                
                # Get existing context if any
                existing_context = {}
                if hasattr(current_agent, 'context') and current_agent.context:
                    if isinstance(current_agent.context, dict):
                        existing_context = current_agent.context
                    else:
                        try:
                            existing_context = json.loads(current_agent.context)
                        except:
                            existing_context = {}
                
                # Get existing chat history
                existing_history = existing_context.get("chat_history", [])
                
                # Prepare the chat history update
                # Convert all messages from memory to serializable form
                current_messages = [{
                    "role": "user" if isinstance(msg, HumanMessage) else
                           "assistant" if isinstance(msg, AIMessage) else
                           "function" if isinstance(msg, FunctionMessage) else "system",
                    "content": str(msg.content),
                    "name": str(msg.name) if isinstance(msg, FunctionMessage) else None,
                    "timestamp": datetime.utcnow().isoformat()
                } for msg in memory.chat_memory.messages]
                
                logger.info(f"Current memory has {len(current_messages)} messages")
                
                # First check - if we had a full history before, verify we're not losing messages
                if len(existing_history) > 50 and len(current_messages) < 50:
                    # If memory has fewer messages than before, we need to preserve history
                    logger.warning(f"Memory has fewer messages ({len(current_messages)}) than history ({len(existing_history)}). Preserving history.")
                    
                    # Keep existing history but add new messages (last turn)
                    # First, get the latest user message
                    latest_user_msg = next((msg for msg in reversed(current_messages) if msg["role"] == "user"), None)
                    # Then get the latest assistant response
                    latest_assistant_msg = next((msg for msg in reversed(current_messages) if msg["role"] == "assistant"), None)
                    
                    # Add these to existing history if they're not already there
                    if latest_user_msg:
                        existing_history.append(latest_user_msg)
                    if latest_assistant_msg:
                        existing_history.append(latest_assistant_msg)
                    
                    combined_history = existing_history
                else:
                    # Use full content from memory since it contains the full conversation
                    combined_history = current_messages
                
                # Sort by timestamp to ensure proper ordering
                combined_history = sorted(combined_history, key=lambda x: x.get("timestamp", ""))
                
                # Limit to last 100 messages if it's getting too large
                if len(combined_history) > 100:
                    combined_history = combined_history[-100:]
                
                # Prepare the context update
                context = {
                    "chat_history": combined_history,
                    "last_updated": datetime.utcnow().isoformat()
                }
                
                # Add summary if available
                if memory.moving_summary_buffer:
                    context["conversation_summary"] = str(memory.moving_summary_buffer)
                
                # Serialize the entire context to a JSON string
                serialized_context = json.dumps(context)
                
                # Log the number of messages being stored
                logger.info(f"Storing {len(combined_history)} messages in agent context")
                
                # Update the agent with the serialized context
                self.update_agent(agent_id, {"context": serialized_context})
                
            except Exception as e:
                logger.error(f"Failed to update agent context: {str(e)}")
                # Continue execution even if context update fails

            return output

        except Exception as e:
            # Error handling
            duration_ms = int((time.time() - start_time) * 1000)
            error_log_data = {
                "agent_id": str(agent_id),
                "request_message": str(message),
                "response_message": f"Error: {str(e)}",
                "input_tokens": str(token_callback.prompt_tokens),
                "output_tokens": str(token_callback.completion_tokens),
                "total_tokens": str(token_callback.total_tokens),
                "requestor_id": str(requestor_id),
                "model_name": str(self.llm.model_name),
                "duration_ms": str(duration_ms),
                "status": "error",
                "error_message": str(e),
                "temperature": str(self.llm.temperature),
                "max_tokens": str(self.llm.max_tokens) if self.llm.max_tokens else "none",
                "cost": str(token_callback.total_cost),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            try:
                self.add_chat_log(error_log_data)
            except Exception as log_error:
                logger.error(f"Failed to save error log: {str(log_error)}")
            
            logger.error(f"Error processing chat message: {str(e)}")
            raise

# Create a global engine instance
agent_engine = AgentEngine() 