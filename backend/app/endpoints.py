from fastapi import APIRouter, HTTPException
from typing import List, Optional
from .models import Agent, AgentCreate, AgentUpdate, AgentStatus, AgentResponse, ChatMessage, ChatLog, ChatLogCreate
from .engine import agent_engine
from .tools import tool_registry
from .vector_store import vector_store
from langchain.schema import Document
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/agents", response_model=Agent)
async def create_agent(agent: AgentCreate):
    """Create a new agent."""
    try:
        logger.info(f"Creating new agent with name: {agent.name}")
        
        # Validate tool names
        for tool_name in agent.tools:
            try:
                tool_registry.get_tool(tool_name)
            except ValueError as e:
                logger.warning(f"Tool {tool_name} not found")
                raise HTTPException(status_code=400, detail=f"Tool {tool_name} not found")
        
        # Create a new agent with default status
        new_agent = Agent(
            name=agent.name,
            description=agent.description,
            prompt=agent.prompt,
            tools=agent.tools,  # Keep as tool names
            hitl_enabled=agent.hitl_enabled,
            status=AgentStatus.IDLE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        logger.info(f"Created agent object with ID: {new_agent.id}")
        
        # Store the agent in ChromaDB
        try:
            stored_agent = agent_engine.create_agent(new_agent)
            logger.info(f"Successfully stored agent in ChromaDB with ID: {stored_agent.id}")
            return stored_agent
        except Exception as e:
            logger.error(f"Failed to store agent in ChromaDB: {str(e)}")
            raise
    except Exception as e:
        logger.error(f"Error creating agent: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agents", response_model=List[Agent])
async def list_agents():
    """List all agents."""
    try:
        return agent_engine.get_agents()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agents/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str):
    """Get a specific agent by ID."""
    try:
        agent = agent_engine.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/agents/{agent_id}", response_model=Agent)
async def update_agent(agent_id: str, agent_update: AgentUpdate):
    """Update an existing agent."""
    try:
        logger.info(f"Received update request for agent ID: {agent_id}")
        logger.info(f"Update data received: {agent_update}")
        
        # Get the agent from the database
        agent = agent_engine.get_agent(agent_id)
        if not agent:
            logger.error(f"Agent not found with ID: {agent_id}")
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Convert agent_update to dict, excluding None values
        update_data = agent_update.dict(exclude_unset=True, exclude_none=True)
        logger.info(f"Processed update data for agent {agent_id}: {update_data}")
        
        # Validate tool names if tools are being updated
        if "tools" in update_data:
            logger.info(f"Validating tools: {update_data['tools']}")
            for tool_name in update_data["tools"]:
                try:
                    tool_registry.get_tool(tool_name)
                except ValueError as e:
                    logger.warning(f"Tool {tool_name} not found")
                    raise HTTPException(status_code=400, detail=f"Tool {tool_name} not found")
        
        # Update the agent
        try:
            updated_agent = agent_engine.update_agent(agent_id, update_data)
            if not updated_agent:
                logger.error(f"Failed to update agent {agent_id} in database")
                raise HTTPException(status_code=500, detail="Failed to update agent")
            logger.info(f"Successfully updated agent {agent_id}")
            return updated_agent
        except Exception as e:
            logger.error(f"Error in agent_engine.update_agent: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
            
    except ValueError as e:
        logger.error(f"Validation error updating agent: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error updating agent: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agents/{agent_id}/start")
async def start_agent(agent_id: str):
    """Start an agent's workflow."""
    try:
        # Get the agent from the database
        agent = agent_engine.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Start the agent
        agent_engine.start_agent(agent)
        
        # Update agent status
        agent_engine.update_agent(agent_id, {"status": AgentStatus.RUNNING})
        
        return {"status": "success", "message": f"Agent {agent_id} started"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error starting agent: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agents/{agent_id}/pause")
async def pause_agent(agent_id: str):
    """Pause an agent's workflow."""
    try:
        # Get the agent from the database
        agent = agent_engine.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Pause the agent
        agent_engine.pause_agent(agent_id)
        
        # Update agent status
        agent_engine.update_agent(agent_id, {"status": AgentStatus.PAUSED})
        
        return {"status": "success", "message": f"Agent {agent_id} paused"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error pausing agent: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agents/{agent_id}/resume")
async def resume_agent(agent_id: str):
    """Resume a paused agent's workflow."""
    try:
        # Get the agent from the database
        agent = agent_engine.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Resume the agent
        agent_engine.resume_agent(agent_id)
        
        # Update agent status
        agent_engine.update_agent(agent_id, {"status": AgentStatus.RUNNING})
        
        return {"status": "success", "message": f"Agent {agent_id} resumed"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error resuming agent: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str):
    """Delete an agent."""
    try:
        # Get the agent from the database
        agent = agent_engine.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Stop the agent if it's running
        if agent.status == AgentStatus.RUNNING:
            agent_engine.pause_agent(agent_id)
        
        # Delete the agent
        success = agent_engine.delete_agent(agent_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete agent")
        
        return {"status": "success", "message": f"Agent {agent_id} deleted"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting agent: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agents/{agent_id}/status")
async def get_agent_status(agent_id: str):
    """Get the current status of an agent."""
    try:
        status = agent_engine.get_agent_status(agent_id)
        return {"status": status}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/tools")
async def list_tools():
    """List all available tools."""
    return tool_registry.list_tools()

@router.post("/vector-store/documents")
async def add_documents(documents: List[dict]):
    """Add documents to the vector store."""
    try:
        # Convert dictionaries to Document objects
        docs = [Document(
            page_content=doc["text"],
            metadata=doc.get("metadata", {})
        ) for doc in documents]
        
        vector_store.add_documents(docs)
        return {"status": "success", "message": f"Added {len(docs)} documents"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/vector-store/search")
async def search_documents(query: str, k: int = 4):
    """Search for similar documents."""
    try:
        results = vector_store.search(query, k=k)
        return {
            "results": [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata
                }
                for doc in results
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/vector-store/search-with-score")
async def search_documents_with_score(query: str, k: int = 4):
    """Search for similar documents with similarity scores."""
    try:
        results = vector_store.search_with_score(query, k=k)
        return {
            "results": [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": score
                }
                for doc, score in results
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/vector-store/collections/{collection_name}")
async def delete_collection(collection_name: str):
    """Delete a collection from the vector store."""
    try:
        vector_store.delete_collection(collection_name)
        return {"status": "success", "message": f"Deleted collection {collection_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agents/{agent_id}/chat", response_model=ChatMessage)
async def chat_with_agent(agent_id: str, message: ChatMessage):
    """Chat with a specific agent."""
    try:
        # Get the agent from ChromaDB
        agent = agent_engine.get_agent(agent_id)  # Synchronous call
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Process the message and get response
        response = await agent_engine.process_chat_message(agent_id, message.content)
        
        return ChatMessage(content=response)
    except Exception as e:
        logger.error(f"Error in chat_with_agent: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agents/{agent_id}/chat-logs", response_model=List[ChatLog])
async def get_agent_chat_logs(agent_id: str):
    """Get all chat logs for a specific agent."""
    try:
        logs = vector_store.get_chat_logs_by_agent(agent_id)
        return logs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agents/{agent_id}/token-usage")
async def get_agent_token_usage(agent_id: str):
    """Get token usage statistics for a specific agent."""
    try:
        return vector_store.get_token_usage_by_agent(agent_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chat-logs/timerange", response_model=List[ChatLog])
async def get_chat_logs_by_timerange(
    start_time: datetime,
    end_time: datetime
):
    """Get chat logs within a specific time range."""
    try:
        logs = vector_store.get_chat_logs_by_timerange(
            start_time.isoformat(),
            end_time.isoformat()
        )
        return logs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 