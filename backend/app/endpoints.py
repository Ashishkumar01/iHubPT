from fastapi import APIRouter, HTTPException, Depends
from typing import List
from .models import Agent, AgentCreate, AgentUpdate, AgentStatus
from .engine import agent_engine
from .tools import tool_registry
from .vector_store import vector_store
from langchain.schema import Document

router = APIRouter()

@router.post("/agents", response_model=Agent)
async def create_agent(agent: AgentCreate):
    """Create a new agent."""
    # Here you would typically save the agent to a database
    # For now, we'll just create an in-memory agent
    new_agent = Agent(**agent.dict())
    return new_agent

@router.get("/agents", response_model=List[Agent])
async def list_agents():
    """List all agents."""
    # Here you would typically fetch agents from a database
    # For now, return an empty list
    return []

@router.get("/agents/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str):
    """Get a specific agent by ID."""
    # Here you would typically fetch the agent from a database
    # For now, raise a 404
    raise HTTPException(status_code=404, detail="Agent not found")

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