from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from enum import Enum
from datetime import datetime

class Tool(BaseModel):
    name: str
    description: str
    parameters: Dict[str, dict]

class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"

class Agent(BaseModel):
    id: Optional[str] = None
    name: str
    description: str
    tools: List[Tool]
    prompt: str
    hitl_enabled: bool = False
    status: AgentStatus = AgentStatus.IDLE
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True

class AgentCreate(BaseModel):
    name: str
    description: str
    tools: List[Tool]
    prompt: str
    hitl_enabled: bool = False

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    tools: Optional[List[Tool]] = None
    prompt: Optional[str] = None
    hitl_enabled: Optional[bool] = None
    status: Optional[AgentStatus] = None 