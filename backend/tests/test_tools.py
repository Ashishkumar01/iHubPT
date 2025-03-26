import pytest
from fastapi import status

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
    response = client.post("/api/v1/tools", json=test_tool.dict())
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == test_tool.name
    assert data["description"] == test_tool.description

def test_register_tool_invalid_data(client):
    response = client.post("/api/v1/tools", json={})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_register_duplicate_tool(client, test_tool):
    # Register the tool first
    client.post("/api/v1/tools", json=test_tool.dict())
    
    # Try to register the same tool again
    response = client.post("/api/v1/tools", json=test_tool.dict())
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already registered" in response.json()["detail"].lower()

def test_unregister_tool(client, test_tool):
    # Register the tool first
    client.post("/api/v1/tools", json=test_tool.dict())
    
    # Unregister the tool
    response = client.delete(f"/api/v1/tools/{test_tool.name}")
    assert response.status_code == status.HTTP_200_OK
    
    # Verify the tool is unregistered
    get_response = client.get(f"/api/v1/tools/{test_tool.name}")
    assert get_response.status_code == status.HTTP_404_NOT_FOUND

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