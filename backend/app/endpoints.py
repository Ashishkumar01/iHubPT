from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from .models import Agent, AgentCreate, AgentUpdate, AgentStatus, AgentResponse, ChatMessage
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

@router.post("/agents/{agent_id}/start")
async def start_agent(agent_id: str):
    """Start an agent's workflow."""
    try:
        # Here you would typically fetch the agent from a database
        # For now, we'll use a dummy agent
        agent = Agent(
            id=agent_id,
            name="Dummy Agent",
            description="A dummy agent for testing",
            tools=[],
            prompt="You are a helpful assistant."
        )
        
        agent_engine.start_agent(agent)
        return {"status": "success", "message": f"Agent {agent_id} started"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/agents/{agent_id}/pause")
async def pause_agent(agent_id: str):
    """Pause an agent's workflow."""
    try:
        agent_engine.pause_agent(agent_id)
        return {"status": "success", "message": f"Agent {agent_id} paused"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/agents/{agent_id}/resume")
async def resume_agent(agent_id: str):
    """Resume a paused agent's workflow."""
    try:
        agent_engine.resume_agent(agent_id)
        return {"status": "success", "message": f"Agent {agent_id} resumed"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

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
        agent = agent_engine.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Process the message and get response
        response = await agent_engine.process_chat_message(agent_id, message.content)
        
        return ChatMessage(content=response)
    except Exception as e:
        logger.error(f"Error in chat_with_agent: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 