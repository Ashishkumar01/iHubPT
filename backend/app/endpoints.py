"""API endpoints for the iHubPT application.

This module defines all the FastAPI endpoints for the application, including
agent management, tool registration, and chat functionality.
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
from .models import Agent, AgentCreate, AgentUpdate, AgentStatus, AgentResponse, ChatMessage, ChatLog, ChatLogCreate
from .engine import agent_engine
from .tools import tool_registry, FUNCTION_MAP, SCHEMA_MAP
from .vector_store import vector_store
from langchain.schema import Document
from datetime import datetime
import logging
from langchain.tools import Tool
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/agents", response_model=Agent)
async def create_agent(agent: AgentCreate):
    """Create a new agent in the system.
    
    Args:
        agent (AgentCreate): The agent configuration data.
        
    Returns:
        Agent: The newly created agent.
        
    Raises:
        HTTPException: If tool validation fails or agent creation fails.
    """
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
    """List all agents in the system.
    
    Returns:
        List[Agent]: List of all agents.
        
    Raises:
        HTTPException: If there's an error retrieving the agents.
    """
    try:
        return agent_engine.get_agents()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agents/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str):
    """Get a specific agent by ID.
    
    Args:
        agent_id (str): The unique identifier of the agent.
        
    Returns:
        Agent: The requested agent.
        
    Raises:
        HTTPException: If the agent is not found or there's an error retrieving it.
    """
    try:
        agent = agent_engine.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/agents/{agent_id}", response_model=Agent)
async def update_agent(agent_id: str, agent_update: AgentUpdate):
    """Update an existing agent's configuration.
    
    Args:
        agent_id (str): The unique identifier of the agent to update.
        agent_update (AgentUpdate): The new configuration for the agent.
        
    Returns:
        Agent: The updated agent.
        
    Raises:
        HTTPException: If the agent is not found, tool validation fails, or update fails.
    """
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
    """Start an agent's workflow.
    
    Args:
        agent_id (str): The unique identifier of the agent to start.
        
    Returns:
        dict: Status message indicating successful start.
        
    Raises:
        HTTPException: If the agent is not found or there's an error starting it.
    """
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
    """Pause an agent's workflow.
    
    Args:
        agent_id (str): The unique identifier of the agent to pause.
        
    Returns:
        dict: Status message indicating successful pause.
        
    Raises:
        HTTPException: If the agent is not found or there's an error pausing it.
    """
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
    """Resume a paused agent's workflow.
    
    Args:
        agent_id (str): The unique identifier of the agent to resume.
        
    Returns:
        dict: Status message indicating successful resume.
        
    Raises:
        HTTPException: If the agent is not found or there's an error resuming it.
    """
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
    """Delete an agent from the system.
    
    Args:
        agent_id (str): The unique identifier of the agent to delete.
        
    Returns:
        dict: Status message indicating successful deletion.
        
    Raises:
        HTTPException: If the agent is not found or there's an error deleting it.
    """
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
    """Get the current status of an agent.
    
    Args:
        agent_id (str): The unique identifier of the agent.
        
    Returns:
        dict: The current status of the agent.
        
    Raises:
        HTTPException: If there's an error retrieving the status.
    """
    try:
        status = agent_engine.get_agent_status(agent_id)
        return {"status": status}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/tools")
async def list_tools():
    """List all available tools in the system.
    
    Returns:
        List[dict]: List of all registered tools with their names and descriptions.
    """
    return tool_registry.list_tools()

@router.delete("/tools/{tool_name}")
async def unregister_tool(tool_name: str):
    """Unregister a tool from the system.
    
    Args:
        tool_name (str): The name of the tool to unregister.
        
    Returns:
        dict: Status message indicating successful unregistration.
        
    Raises:
        HTTPException: If the tool is not found or there's an error unregistering it.
    """
    try:
        tool_registry.unregister_tool(tool_name)
        return {"message": f"Tool {tool_name} unregistered successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error unregistering tool: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tools", response_model=dict)
async def register_tool(tool: dict):
    """Register a new tool in the system.
    
    Args:
        tool (dict): Tool configuration containing:
            - name (str): Name of the tool
            - description (str): Description of what the tool does
            - func (str): Name of the function to execute
            - schema_name (str, optional): Name of the schema for tool parameters
            
    Returns:
        dict: Registration status and tool details.
        
    Raises:
        HTTPException: If required fields are missing, tool already exists,
            function not found, or registration fails.
    """
    try:
        # Validate required fields
        if not tool.get("name") or not tool.get("description") or not tool.get("func"):
            raise HTTPException(status_code=400, detail="Tool name, description, and function name are required")
            
        # Check if tool already exists
        try:
            tool_registry.get_tool(tool["name"])
            raise HTTPException(status_code=400, detail=f"Tool {tool['name']} is already registered")
        except ValueError:
            pass
            
        # Validate function exists
        if tool["func"] not in FUNCTION_MAP:
            raise HTTPException(status_code=400, detail=f"Function {tool['func']} not found in available functions")
            
        # Get the function and schema
        func = FUNCTION_MAP[tool["func"]]
        schema_name = tool.get("schema_name")
        schema_class = SCHEMA_MAP.get(schema_name) if schema_name else None
        
        # Create a new tool
        new_tool = Tool.from_function(
            func=func,
            name=tool["name"],
            description=tool["description"],
            args_schema=schema_class
        )
        
        # Register the tool
        tool_registry.register_tool(new_tool)
        
        return {
            "message": f"Tool {tool['name']} registered successfully",
            "tool": {
                "name": new_tool.name,
                "description": new_tool.description,
                "parameters": new_tool.args_schema.schema() if new_tool.args_schema else {}
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering tool: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/vector-store/documents")
async def add_documents(documents: List[dict]):
    """Add documents to the vector store for semantic search.
    
    Args:
        documents (List[dict]): List of documents to add, each containing:
            - text (str): The document content
            - metadata (dict, optional): Additional metadata for the document
            
    Returns:
        dict: Status message indicating successful addition of documents.
        
    Raises:
        HTTPException: If there's an error adding the documents.
    """
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
    """Search for similar documents in the vector store.
    
    Args:
        query (str): The search query text.
        k (int, optional): Number of results to return. Defaults to 4.
        
    Returns:
        dict: Dictionary containing search results with content and metadata.
        
    Raises:
        HTTPException: If there's an error performing the search.
    """
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
    """Search for similar documents with similarity scores.
    
    Args:
        query (str): The search query text.
        k (int, optional): Number of results to return. Defaults to 4.
        
    Returns:
        dict: Dictionary containing search results with content, metadata, and similarity scores.
        
    Raises:
        HTTPException: If there's an error performing the search.
    """
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
    """Delete a collection from the vector store.
    
    Args:
        collection_name (str): Name of the collection to delete.
        
    Returns:
        dict: Status message indicating successful deletion.
        
    Raises:
        HTTPException: If there's an error deleting the collection.
    """
    try:
        vector_store.delete_collection(collection_name)
        return {"status": "success", "message": f"Deleted collection {collection_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agents/{agent_id}/chat", response_model=ChatMessage)
async def chat_with_agent(agent_id: str, message: ChatMessage):
    """Send a chat message to a specific agent and get its response.
    
    Args:
        agent_id (str): The unique identifier of the agent to chat with.
        message (ChatMessage): The chat message to send.
        
    Returns:
        ChatMessage: The agent's response message.
        
    Raises:
        HTTPException: If the agent is not found or there's an error processing the message.
    """
    try:
        # Get the agent from ChromaDB
        agent = agent_engine.get_agent(agent_id)  # Synchronous call
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Process the message and get response
        response = await agent_engine.process_chat_message(
            agent_id=agent_id,
            message=message.content
        )
        
        return ChatMessage(content=response)
    except Exception as e:
        logger.error(f"Error in chat_with_agent: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agents/{agent_id}/chat-logs", response_model=List[ChatLog])
async def get_agent_chat_logs(agent_id: str):
    """Get all chat logs for a specific agent.
    
    Args:
        agent_id (str): The unique identifier of the agent.
        
    Returns:
        List[ChatLog]: List of chat logs for the specified agent.
        
    Raises:
        HTTPException: If there's an error retrieving the chat logs.
    """
    try:
        # Get logs from the vector store instead of agent_engine
        logs = vector_store.get_chat_logs_by_agent(agent_id)
        return logs
    except Exception as e:
        logger.error(f"Error getting chat logs for agent {agent_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agents/{agent_id}/token-usage")
async def get_agent_token_usage(agent_id: str):
    """Get token usage statistics for a specific agent.
    
    Args:
        agent_id (str): The unique identifier of the agent.
        
    Returns:
        dict: Token usage statistics for the agent.
        
    Raises:
        HTTPException: If there's an error retrieving the token usage.
    """
    try:
        return vector_store.get_token_usage_by_agent(agent_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chat-logs/timerange", response_model=List[ChatLog])
async def get_chat_logs_by_timerange(
    start_time: datetime,
    end_time: datetime,
    agent_id: Optional[str] = None
):
    """Get chat logs within a specific time range.
    
    Args:
        start_time (datetime): Start of the time range.
        end_time (datetime): End of the time range.
        agent_id (Optional[str]): Optional agent ID to filter logs by.
        
    Returns:
        List[ChatLog]: List of chat logs within the specified time range.
        
    Raises:
        HTTPException: If there's an error retrieving the chat logs.
    """
    try:
        # Get logs from the vector store instead of agent_engine
        if agent_id:
            logs = vector_store.get_chat_logs_by_agent_and_timerange(
                agent_id,
                start_time.isoformat(),
                end_time.isoformat()
            )
        else:
            logs = vector_store.get_chat_logs_by_timerange(
                start_time.isoformat(),
                end_time.isoformat()
            )
        logger.info(f"Retrieved {len(logs)} chat logs between {start_time} and {end_time}")
        return logs
    except Exception as e:
        logger.error(f"Error getting chat logs by timerange: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tools/{tool_name}/execute", response_model=dict)
async def execute_tool(tool_name: str, parameters: dict):
    """Execute a tool with given parameters.
    
    Args:
        tool_name (str): Name of the tool to execute.
        parameters (dict): Parameters to pass to the tool.
        
    Returns:
        dict: Result of the tool execution.
        
    Raises:
        HTTPException: If the tool is not found or there's an error executing it.
    """
    try:
        # Get the tool
        tool = tool_registry.get_tool(tool_name)
        
        # Execute the tool with parameters
        result = tool.func(**parameters)
        
        # Return the result
        if isinstance(result, str) and result.startswith('{'):
            # If result is a JSON string, parse it
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                return {"result": result}
        else:
            return {"result": result}
            
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test/add-sample-chat-logs", response_model=dict)
async def add_sample_chat_logs(agent_id: str = None):
    """Add sample chat logs for testing purposes.
    
    Args:
        agent_id (Optional[str]): Optional agent ID to add logs for. If not provided,
            uses the first available agent.
            
    Returns:
        dict: Status message indicating successful addition of sample logs.
        
    Raises:
        HTTPException: If no agents are found or there's an error adding the logs.
    """
    try:
        if not agent_id:
            # Get the first agent in the database
            agents = agent_engine.get_agents()
            if not agents:
                raise HTTPException(status_code=404, detail="No agents found")
            agent_id = str(agents[0].id)
        
        # Create sample chat logs
        for i in range(1, 6):
            chat_log_data = {
                "agent_id": str(agent_id),
                "request_message": f"Test request {i}",
                "response_message": f"Test response {i}",
                "input_tokens": 100 * i,
                "output_tokens": 50 * i,
                "total_tokens": 150 * i,
                "requestor_id": "test-user",
                "model_name": "gpt-4-turbo-preview",
                "duration_ms": 1000 * i,
                "status": "success",
                "temperature": 0.7,
                "max_tokens": "4000",
                "cost": 0.001 * i,
                "timestamp": datetime.utcnow().isoformat(),
                "tool_calls": "[]",
                "has_tool_calls": "false",
                "memory_summary": "",
                "has_memory": "false",
                "user": "Administrator",
                "department": "Post Trade"
            }
            
            # Add to chat logs using vector_store
            vector_store.add_chat_log(chat_log_data)
            
        return {"status": "success", "message": f"Added 5 sample chat logs for agent {agent_id}"}
    except Exception as e:
        logger.error(f"Error adding sample chat logs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 