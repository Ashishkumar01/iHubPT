from typing import Dict, Any, List
from langchain.tools import BaseTool, Tool
from pydantic import BaseModel

class ExampleToolArgs(BaseModel):
    input_text: str

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register_tool(self, tool: BaseTool) -> None:
        """Register a new tool in the registry."""
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> BaseTool:
        """Get a tool by name."""
        if name not in self._tools:
            raise ValueError(f"Tool {name} not found")
        return self._tools[name]

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools with their descriptions."""
        tools_list = []
        for name, tool in self._tools.items():
            tool_info = {
                "name": name,
                "description": tool.description,
                "parameters": {}
            }
            if tool.args_schema:
                tool_info["parameters"] = tool.args_schema.schema()
            tools_list.append(tool_info)
        return tools_list

# Create a global tool registry instance
tool_registry = ToolRegistry()

def example_tool(input_text: str) -> str:
    """An example tool that processes text."""
    return f"Processed: {input_text}"

# Register the example tool
tool_registry.register_tool(
    Tool.from_function(
        func=example_tool,
        name="example_tool",
        description="An example tool that processes text input",
        args_schema=ExampleToolArgs
    )
) 