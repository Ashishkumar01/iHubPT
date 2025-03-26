import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models import Agent, AgentCreate, Tool
from app.engine import agent_engine
from app.tools import tool_registry
from app.vector_store import vector_store

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def test_agent():
    return Agent(
        id="test-id",
        name="Test Agent",
        description="A test agent",
        tools=[],
        prompt="You are a helpful assistant.",
        hitl_enabled=False,
        status="idle"
    )

@pytest.fixture
def test_agent_create():
    return AgentCreate(
        name="Test Agent",
        description="A test agent",
        tools=[],
        prompt="You are a helpful assistant.",
        hitl_enabled=False
    )

@pytest.fixture
def test_tool():
    return Tool(
        name="test_tool",
        description="A test tool",
        parameters={}
    )

@pytest.fixture(autouse=True)
def cleanup():
    # Clear any existing data before each test
    agent_engine._active_agents.clear()
    tool_registry._tools.clear()
    yield
    # Clean up after each test
    agent_engine._active_agents.clear()
    tool_registry._tools.clear() 