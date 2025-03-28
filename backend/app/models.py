from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime
import uuid
from uuid import UUID, uuid4

class Tool(BaseModel):
    """Model for tools that can be used by agents."""
    name: str = Field(..., description="Name of the tool")
    description: str = Field(..., description="Description of what the tool does")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters required by the tool")

class AgentStatus(str, Enum):
    """Enum for agent status."""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class Agent(BaseModel):
    """Base model for an agent."""
    id: UUID = Field(default_factory=uuid4, description="Unique identifier for the agent")
    name: str = Field(..., description="Name of the agent")
    description: str = Field(..., description="Description of the agent")
    prompt: str = Field(..., description="System prompt for the agent")
    tools: List[str] = Field(default_factory=list, description="List of tool names the agent can use")
    hitl_enabled: bool = Field(default=False, description="Whether human-in-the-loop is enabled")
    status: AgentStatus = Field(default=AgentStatus.IDLE, description="Current status of the agent")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context for the agent")

class AgentCreate(BaseModel):
    """Model for creating a new agent."""
    name: str = Field(..., description="Name of the agent")
    description: str = Field(..., description="Description of the agent")
    prompt: str = Field(..., description="System prompt for the agent")
    tools: List[str] = Field(default_factory=list, description="List of tool names the agent can use")
    hitl_enabled: bool = Field(default=False, description="Whether human-in-the-loop is enabled")

class AgentUpdate(BaseModel):
    """Model for updating an existing agent."""
    name: Optional[str] = None
    description: Optional[str] = None
    prompt: Optional[str] = None
    tools: Optional[List[str]] = None
    hitl_enabled: Optional[bool] = None
    status: Optional[AgentStatus] = None

class AgentResponse(BaseModel):
    """Model for agent responses."""
    id: UUID
    name: str
    description: str
    status: AgentStatus
    created_at: datetime
    updated_at: datetime

class ChatMessage(BaseModel):
    """Model for chat messages."""
    content: str = Field(..., description="The content of the chat message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of the message") 