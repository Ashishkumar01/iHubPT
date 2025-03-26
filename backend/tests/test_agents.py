import pytest
from fastapi import status
from app.models import AgentStatus

def test_create_agent(client, test_agent_create):
    response = client.post("/api/v1/agents", json=test_agent_create.dict())
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == test_agent_create.name
    assert data["description"] == test_agent_create.description
    assert data["prompt"] == test_agent_create.prompt
    assert data["hitl_enabled"] == test_agent_create.hitl_enabled
    assert data["status"] == AgentStatus.IDLE
    assert data["id"] is not None

def test_create_agent_invalid_data(client):
    response = client.post("/api/v1/agents", json={})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_get_agents(client, test_agent):
    # Create an agent first
    client.post("/api/v1/agents", json=test_agent.dict())
    
    response = client.get("/api/v1/agents")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["name"] == test_agent.name

def test_get_agent(client, test_agent):
    # Create an agent first
    create_response = client.post("/api/v1/agents", json=test_agent.dict())
    agent_id = create_response.json()["id"]
    
    response = client.get(f"/api/v1/agents/{agent_id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == test_agent.name
    assert data["id"] == agent_id

def test_get_nonexistent_agent(client):
    response = client.get("/api/v1/agents/nonexistent-id")
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_update_agent(client, test_agent):
    # Create an agent first
    create_response = client.post("/api/v1/agents", json=test_agent.dict())
    agent_id = create_response.json()["id"]
    
    # Update the agent
    update_data = {"name": "Updated Agent"}
    response = client.put(f"/api/v1/agents/{agent_id}", json=update_data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "Updated Agent"
    assert data["description"] == test_agent.description

def test_delete_agent(client, test_agent):
    # Create an agent first
    create_response = client.post("/api/v1/agents", json=test_agent.dict())
    agent_id = create_response.json()["id"]
    
    # Delete the agent
    response = client.delete(f"/api/v1/agents/{agent_id}")
    assert response.status_code == status.HTTP_200_OK
    
    # Verify the agent is deleted
    get_response = client.get(f"/api/v1/agents/{agent_id}")
    assert get_response.status_code == status.HTTP_404_NOT_FOUND

def test_agent_lifecycle(client, test_agent):
    # Create an agent
    create_response = client.post("/api/v1/agents", json=test_agent.dict())
    agent_id = create_response.json()["id"]
    
    # Start the agent
    start_response = client.post(f"/api/v1/agents/{agent_id}/start")
    assert start_response.status_code == status.HTTP_200_OK
    assert start_response.json()["status"] == "success"
    
    # Check agent status
    status_response = client.get(f"/api/v1/agents/{agent_id}/status")
    assert status_response.status_code == status.HTTP_200_OK
    assert status_response.json()["status"] == AgentStatus.RUNNING
    
    # Pause the agent
    pause_response = client.post(f"/api/v1/agents/{agent_id}/pause")
    assert pause_response.status_code == status.HTTP_200_OK
    assert pause_response.json()["status"] == "success"
    
    # Check agent status
    status_response = client.get(f"/api/v1/agents/{agent_id}/status")
    assert status_response.status_code == status.HTTP_200_OK
    assert status_response.json()["status"] == AgentStatus.PAUSED
    
    # Resume the agent
    resume_response = client.post(f"/api/v1/agents/{agent_id}/resume")
    assert resume_response.status_code == status.HTTP_200_OK
    assert resume_response.json()["status"] == "success"
    
    # Check agent status
    status_response = client.get(f"/api/v1/agents/{agent_id}/status")
    assert status_response.status_code == status.HTTP_200_OK
    assert status_response.json()["status"] == AgentStatus.RUNNING 