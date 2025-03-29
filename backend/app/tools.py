from typing import Dict, Any, List
from langchain.tools import BaseTool, Tool
from pydantic import BaseModel
import os
from pathlib import Path

class ExampleToolArgs(BaseModel):
    input_text: str

class CalculatorToolArgs(BaseModel):
    operation: str
    x: float
    y: float

class RuleSearchArgs(BaseModel):
    query: str
    
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

def calculator_tool(operation: str, x: float, y: float) -> str:
    """A calculator tool that performs basic math operations."""
    operation = operation.lower()
    try:
        if operation == "add":
            result = x + y
        elif operation == "subtract":
            result = x - y
        elif operation == "multiply":
            result = x * y
        elif operation == "divide":
            if y == 0:
                return "Error: Division by zero"
            result = x / y
        else:
            return f"Error: Unknown operation '{operation}'. Supported operations are: add, subtract, multiply, divide"
        
        return f"{x} {operation} {y} = {result}"
    except Exception as e:
        return f"Error: {str(e)}"

def search_rules(query: str) -> str:
    """
    Search through the rules file and return relevant rules based on the query.
    Uses basic keyword matching to find relevant rules.
    """
    try:
        # Get the rules file path
        rules_file = Path(__file__).parent / "data" / "rules.txt"
        
        if not rules_file.exists():
            return "Error: Rules file not found."
        
        # Read the rules file
        with open(rules_file, 'r') as f:
            rules_text = f.read()
        
        # Split the rules into individual rules
        rules = rules_text.split('Rule')[1:]  # Skip the first empty split
        
        # Convert query to lowercase for case-insensitive search
        query = query.lower()
        
        # Search for relevant rules
        relevant_rules = []
        for rule in rules:
            if query in rule.lower():
                # Clean up the rule text and add it to results
                clean_rule = f"Rule{rule.strip()}"
                relevant_rules.append(clean_rule)
        
        if not relevant_rules:
            return f"No rules found matching the query: {query}"
        
        # Format the response
        response = "Found the following relevant rules:\n\n"
        response += "\n\n".join(relevant_rules)
        return response
        
    except Exception as e:
        return f"Error searching rules: {str(e)}"

# Register the example tool
tool_registry.register_tool(
    Tool.from_function(
        func=example_tool,
        name="example_tool",
        description="An example tool that processes text input",
        args_schema=ExampleToolArgs
    )
)

# Register the calculator tool
tool_registry.register_tool(
    Tool.from_function(
        func=calculator_tool,
        name="calculator",
        description="A calculator that can perform basic math operations (add, subtract, multiply, divide) on two numbers",
        args_schema=CalculatorToolArgs
    )
)

# Register the rules search tool
tool_registry.register_tool(
    Tool.from_function(
        func=search_rules,
        name="search_rules",
        description="Search through the company rules and policies to find relevant information. Provide keywords or topics to search for.",
        args_schema=RuleSearchArgs
    )
) 