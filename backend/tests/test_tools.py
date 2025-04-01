import pytest
from fastapi import status
from app.tools import tool_registry
from app.models import Tool
import os
import shutil

@pytest.fixture(autouse=True)
def cleanup():
    """Clean up before and after each test."""
    # Clear in-memory tools
    tool_registry._tools.clear()
    
    # Clear ChromaDB collection
    if hasattr(tool_registry, 'collection'):
        tool_registry.collection.delete(where={})
    
    yield
    
    # Clean up after test
    tool_registry._tools.clear()
    if hasattr(tool_registry, 'collection'):
        tool_registry.collection.delete(where={})

@pytest.fixture
def test_tool():
    """Create a test tool."""
    return Tool(
        name="test_tool",
        description="A test tool for testing",
        parameters={
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "Input parameter"
                }
            },
            "required": ["input"]
        }
    )

def test_get_tools(client):
    response = client.get("/api/v1/tools")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)

def test_get_tool(client, test_tool):
    # Register a test tool first
    client.post("/api/v1/tools", json=test_tool.dict())
    
    response = client.get(f"/api/v1/tools/{test_tool.name}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == test_tool.name
    assert data["description"] == test_tool.description

def test_get_nonexistent_tool(client):
    response = client.get("/api/v1/tools/nonexistent-tool")
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_register_tool(client, test_tool):
    """Test registering a new tool."""
    response = client.post("/api/v1/tools", json=test_tool.dict())
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == test_tool.name
    assert data["description"] == test_tool.description
    
    # Verify tool is persisted in ChromaDB
    results = tool_registry.collection.get(ids=[test_tool.name])
    assert results and results['ids'] == [test_tool.name]

def test_register_tool_invalid_data(client):
    response = client.post("/api/v1/tools", json={})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_register_duplicate_tool(client, test_tool):
    """Test registering a duplicate tool."""
    # Register the tool first
    client.post("/api/v1/tools", json=test_tool.dict())
    
    # Try to register the same tool again
    response = client.post("/api/v1/tools", json=test_tool.dict())
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already registered" in response.json()["detail"].lower()

def test_unregister_tool(client, test_tool):
    """Test unregistering a tool."""
    # Register the tool first
    client.post("/api/v1/tools", json=test_tool.dict())
    
    # Unregister the tool
    response = client.delete(f"/api/v1/tools/{test_tool.name}")
    assert response.status_code == status.HTTP_200_OK
    
    # Verify the tool is removed from ChromaDB
    results = tool_registry.collection.get(ids=[test_tool.name])
    assert not results or not results['ids']

def test_unregister_nonexistent_tool(client):
    response = client.delete("/api/v1/tools/nonexistent-tool")
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_tool_execution(client, test_tool):
    # Register the tool first
    client.post("/api/v1/tools", json=test_tool.dict())
    
    # Execute the tool
    response = client.post(f"/api/v1/tools/{test_tool.name}/execute", json={})
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "result" in data 

def test_list_tools(client, test_tool):
    """Test listing all tools."""
    # Register a test tool
    client.post("/api/v1/tools", json=test_tool.dict())
    
    response = client.get("/api/v1/tools")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert any(tool["name"] == test_tool.name for tool in data)

def test_tool_persistence():
    """Test that tools persist between registry instances."""
    # Create a new tool
    test_tool = Tool(
        name="persistence_test_tool",
        description="A tool to test persistence",
        parameters={
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "Input parameter"
                }
            },
            "required": ["input"]
        }
    )
    
    # Register the tool
    tool_registry.register_tool(test_tool)
    
    # Create a new registry instance
    from app.tools import ToolRegistry
    new_registry = ToolRegistry()
    
    # Verify the tool is loaded from ChromaDB
    assert test_tool.name in new_registry._tools
    loaded_tool = new_registry.get_tool(test_tool.name)
    assert loaded_tool.name == test_tool.name
    assert loaded_tool.description == test_tool.description 