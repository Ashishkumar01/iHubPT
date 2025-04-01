"""Data models for the iHubPT application.

This module contains Pydantic models that define the data structures used throughout
the application, including agents, tools, chat messages, and logging.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime
import uuid
from uuid import UUID, uuid4
import json

# Constants
DEFAULT_PROMPT = """You are a helpful AI assistant. You aim to provide clear, accurate, and helpful responses while maintaining a professional and friendly tone."""

class Tool(BaseModel):
    """Model representing a tool that can be used by agents.
    
    Attributes:
        name (str): The unique identifier name of the tool.
        description (str): A detailed description of what the tool does.
        parameters (Dict[str, Any]): Dictionary of parameters required by the tool.
    """
    name: str = Field(..., description="Name of the tool")
    description: str = Field(..., description="Description of what the tool does")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters required by the tool")

class AgentStatus(str, Enum):
    """Enumeration of possible states for an agent.
    
    Attributes:
        IDLE: Agent is ready but not currently processing.
        RUNNING: Agent is actively processing a task.
        PAUSED: Agent is temporarily paused.
        COMPLETED: Agent has finished its task successfully.
        FAILED: Agent encountered an error during execution.
        ERROR: Agent is in an error state.
        CREATED: Agent has been created but not yet started.
    """
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ERROR = "ERROR"
    CREATED = "CREATED"

class Agent(BaseModel):
    """Base model for an AI agent in the system.
    
    This class represents an AI agent with its configuration, state, and capabilities.
    
    Attributes:
        id (UUID): Unique identifier for the agent.
        name (str): Display name of the agent.
        description (str): Detailed description of the agent's purpose.
        prompt (str): System prompt that defines the agent's behavior.
        tools (List[str]): List of tool names the agent can use.
        hitl_enabled (bool): Whether human-in-the-loop interaction is enabled.
        status (AgentStatus): Current operational status of the agent.
        created_at (datetime): Timestamp when the agent was created.
        updated_at (datetime): Timestamp of the last update to the agent.
        context (Optional[Dict[str, Any]]): Additional context data for the agent.
    """
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str
    prompt: str = Field(default=DEFAULT_PROMPT)
    tools: List[str] = Field(default_factory=list)
    hitl_enabled: bool = Field(default=False)
    status: AgentStatus = Field(default=AgentStatus.CREATED)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    context: Optional[Dict[str, Any]] = Field(default=None)
    
    class Config:
        """Pydantic configuration for JSON serialization."""
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat(),
            AgentStatus: lambda v: v.value
        }
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert the agent to a dictionary with serialized values.
        
        Returns:
            Dict[str, Any]: Dictionary containing all agent fields with proper serialization.
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "prompt": self.prompt,
            "tools": json.dumps(self.tools),
            "hitl_enabled": str(self.hitl_enabled).lower(),
            "status": self.status.value.upper(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "context": json.dumps(self.context) if self.context else "{}"
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Agent":
        """Create an Agent instance from a dictionary.
        
        Args:
            data (Dict[str, Any]): Dictionary containing agent data.
            
        Returns:
            Agent: New Agent instance created from the dictionary.
            
        Raises:
            ValueError: If the dictionary data is invalid or missing required fields.
        """
        try:
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
            return cls(**agent_data)
        except Exception as e:
            raise ValueError(f"Failed to create Agent from dictionary: {str(e)}")

class AgentCreate(BaseModel):
    """Model for creating a new agent.
    
    Attributes:
        name (str): Display name for the new agent.
        description (str): Detailed description of the agent's purpose.
        prompt (str): System prompt that defines the agent's behavior.
        tools (List[str]): List of tool names the agent can use.
        hitl_enabled (bool): Whether human-in-the-loop interaction is enabled.
    """
    name: str = Field(..., description="Name of the agent")
    description: str = Field(..., description="Description of the agent")
    prompt: str = Field(..., description="System prompt for the agent")
    tools: List[str] = Field(default_factory=list, description="List of tool names the agent can use")
    hitl_enabled: bool = Field(default=False, description="Whether human-in-the-loop is enabled")

class AgentUpdate(BaseModel):
    """Model for updating an existing agent.
    
    All fields are optional, allowing partial updates to the agent.
    
    Attributes:
        name (Optional[str]): New display name for the agent.
        description (Optional[str]): New description of the agent's purpose.
        prompt (Optional[str]): New system prompt for the agent.
        tools (Optional[List[str]]): Updated list of tool names.
        hitl_enabled (Optional[bool]): Updated human-in-the-loop setting.
        status (Optional[AgentStatus]): New operational status.
    """
    name: Optional[str] = None
    description: Optional[str] = None
    prompt: Optional[str] = None
    tools: Optional[List[str]] = None
    hitl_enabled: Optional[bool] = None
    status: Optional[AgentStatus] = None

class AgentResponse(BaseModel):
    """Model for agent responses in API endpoints.
    
    Attributes:
        id (UUID): Unique identifier of the agent.
        name (str): Display name of the agent.
        description (str): Description of the agent's purpose.
        status (AgentStatus): Current operational status.
        created_at (datetime): Creation timestamp.
        updated_at (datetime): Last update timestamp.
    """
    id: UUID
    name: str
    description: str
    status: AgentStatus
    created_at: datetime
    updated_at: datetime

class ChatMessage(BaseModel):
    """Model for chat messages between users and agents.
    
    Attributes:
        content (str): The actual message content.
        chat_history (Optional[List[Dict[str, Any]]]): Previous messages in the conversation.
        timestamp (Optional[datetime]): When the message was sent.
    """
    content: str = Field(..., description="The content of the message")
    chat_history: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Optional chat history")
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Timestamp of the message")

class ChatLog(BaseModel):
    """Model for logging chat interactions with agents.
    
    This model captures detailed information about each interaction with an agent,
    including performance metrics, token usage, and any errors encountered.
    
    Attributes:
        id (str): Unique identifier for the log entry.
        agent_id (str): ID of the agent involved in the interaction.
        timestamp (str): When the interaction occurred.
        request_message (str): The user's input message.
        response_message (str): The agent's response.
        input_tokens (int): Number of tokens in the input.
        output_tokens (int): Number of tokens in the output.
        total_tokens (int): Total tokens used in the interaction.
        requestor_id (str): ID of the user making the request.
        model_name (str): Name of the AI model used.
        duration_ms (int): Time taken for the interaction in milliseconds.
        status (str): Status of the interaction.
        content (Optional[str]): Additional content or context.
        temperature (float): Temperature setting used for generation.
        max_tokens (str): Maximum tokens allowed for generation.
        cost (float): Cost of the interaction.
        tool_calls (str): JSON string of tool calls made.
        has_tool_calls (str): Whether tools were used.
        memory_summary (str): Summary of memory usage.
        has_memory (str): Whether memory was used.
        error_message (Optional[str]): Any error messages.
        user (Optional[str]): Username of the requestor.
        department (Optional[str]): Department of the requestor.
    """
    id: str
    agent_id: str
    timestamp: str
    request_message: str
    response_message: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    requestor_id: str
    model_name: str
    duration_ms: int
    status: str
    content: Optional[str] = None
    temperature: float = 0.0
    max_tokens: str = "none"
    cost: float = 0.0
    tool_calls: str = "[]"
    has_tool_calls: str = "false"
    memory_summary: str = ""
    has_memory: str = "false"
    error_message: Optional[str] = None
    user: Optional[str] = None
    department: Optional[str] = "Post Trade"

class ChatLogCreate(BaseModel):
    """Model for creating a new chat log entry.
    
    Attributes:
        agent_id (str): ID of the agent involved in the interaction.
        request_message (str): The user's input message.
        response_message (str): The agent's response.
        input_tokens (int): Number of tokens in the input.
        output_tokens (int): Number of tokens in the output.
        total_tokens (int): Total tokens used in the interaction.
        requestor_id (str): ID of the user making the request.
        model_name (str): Name of the AI model used.
        duration_ms (int): Time taken for the interaction in milliseconds.
        status (str): Status of the interaction.
        error_message (Optional[str]): Any error messages.
        metadata (Optional[Dict]): Additional metadata about the interaction.
    """
    agent_id: str
    request_message: str
    response_message: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    requestor_id: str = "administrator"
    model_name: str
    duration_ms: int
    status: str
    error_message: Optional[str] = None
    metadata: Optional[Dict] = None