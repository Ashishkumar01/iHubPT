from typing import Dict, Any, List, Type, Optional
from langchain.tools import BaseTool, Tool, StructuredTool
from pydantic import BaseModel, Field, create_model
import os
from pathlib import Path
import json
import chromadb
import logging
from .mailman import (
    get_unread_emails_json,
    mark_email_as_read,
    mark_email_as_spam,
    get_email_labels,
    create_email_label,
    attach_label_to_email
)
from pydantic import validator

logger = logging.getLogger(__name__)

class ExampleToolArgs(BaseModel):
    input_text: str

class CalculatorToolArgs(BaseModel):
    operation: str
    num1: float
    num2: float

class RuleSearchArgs(BaseModel):
    query: str

class GetUnreadEmailsArgs(BaseModel):
    """Arguments for getting unread emails."""
    max_results: Optional[int] = Field(
        default=10,
        description="Maximum number of unread emails to fetch"
    )

class MarkEmailArgs(BaseModel):
    """Arguments for marking email actions."""
    message_id: str = Field(
        description="The ID of the message to perform action on"
    )

class CreateLabelArgs(BaseModel):
    """Arguments for creating a label."""
    label_name: str = Field(
        description="The name of the label to create"
    )

class AttachLabelArgs(BaseModel):
    """Arguments for attaching a label to an email."""
    message_id: str = Field(
        description="The ID of the message to label (this should be the actual Gmail message ID, not the full email address)"
    )
    label_id: str = Field(
        description="The ID of the label to attach"
    )
    
    @validator('message_id')
    def validate_message_id(cls, v):
        """Validate that the message ID is properly formatted."""
        # Check if it looks like an email address format
        if v.startswith('<') and v.endswith('>') and '@' in v:
            # This appears to be an email address format, not a message ID
            raise ValueError("Invalid message ID format. Please provide the actual Gmail message ID, not the email address.")
        
        # Remove any leading/trailing whitespace
        return v.strip()

# Map of schema names to their implementations
SCHEMA_MAP = {
    'ExampleToolArgs': ExampleToolArgs,
    'CalculatorToolArgs': CalculatorToolArgs,
    'RuleSearchArgs': RuleSearchArgs,
    'GetUnreadEmailsArgs': GetUnreadEmailsArgs,
    'MarkEmailArgs': MarkEmailArgs,
    'CreateLabelArgs': CreateLabelArgs,
    'AttachLabelArgs': AttachLabelArgs
}

def example_tool(input_text: str) -> str:
    """An example tool that processes text."""
    return f"Processed: {input_text}"

def calculator_tool(operation: str, num1: float, num2: float) -> float:
    """A calculator that can perform basic math operations."""
    operations = {
        "add": lambda x, y: x + y,
        "subtract": lambda x, y: x - y,
        "multiply": lambda x, y: x * y,
        "divide": lambda x, y: x / y if y != 0 else float('inf')
    }
    if operation not in operations:
        raise ValueError(f"Operation {operation} not supported")
    return operations[operation](num1, num2)

def search_rules(query: str) -> str:
    """Search through company rules and policies."""
    # This is a placeholder implementation
    return f"Searching rules for: {query}"

def gmail_get_unread(max_results: int = 10) -> str:
    """Get unread emails from Gmail and provide a natural summary."""
    try:
        # Get raw email data
        raw_response = get_unread_emails_json(max_results)
        
        try:
            # Parse the JSON response
            data = json.loads(raw_response) if isinstance(raw_response, str) else raw_response
            
            # Handle error responses
            if not isinstance(data, dict):
                return "I encountered an error: Invalid response format from email service."
                
            if data.get("success") == False:
                return f"I encountered an error: {data.get('message', data.get('error', 'Unknown error'))}"
            
            # Check if we have the message field directly (new format)
            if "message" in data and isinstance(data["message"], str):
                return data["message"]
                
            # Check for emails in the expected location
            emails = data.get('emails', [])
            if not emails:
                return "You have no unread emails at the moment."
                
            # Create a natural language summary
            parts = []
            
            # Overview
            total = len(emails)
            parts.append(f"You have {total} unread email{'s' if total != 1 else ''}.")
            
            # Process each email
            for idx, email in enumerate(emails, 1):
                # Extract email details
                subject = email.get('subject', 'No subject')
                sender_name = email.get('sender', {}).get('name', 'Unknown sender')
                sender_email = email.get('sender', {}).get('email', '')
                content = email.get('content', '')
                message_id = email.get('id', '')  # Get the message ID
                
                # Format the email summary with message ID
                parts.append(f"\n{idx}. From: {sender_name} <{sender_email}>")
                parts.append(f"   Subject: {subject}")
                parts.append(f"   Message ID: {message_id}")  # Always include message ID
                if content:
                    # Clean and truncate content if needed
                    cleaned_content = content.replace('\r', '').replace('\n\n', '\n').strip()
                    if len(cleaned_content) > 300:
                        cleaned_content = cleaned_content[:297] + "..."
                    parts.append(f"   Content: {cleaned_content}")
                
                # Add any labels or important markers
                labels = email.get('labels', [])
                if 'IMPORTANT' in labels:
                    parts.append("   (This email is marked as important)")
                
                # Add any attachments notice
                if email.get('has_attachments'):
                    parts.append("   (This email has attachments)")
                    
            # Add helpful suggestions with clear instructions about message IDs
            parts.append("\nWould you like me to help you with any of the following actions?")
            parts.append("- Mark any of these emails as read (just provide the message ID)")
            parts.append("- Add labels to organize them (provide the message ID and label name)")
            parts.append("- Show you more details about any specific email")
            
            return "\n".join(parts)
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)} for data: {raw_response[:100]}...")
            # If the response is already a formatted string, return it
            if isinstance(raw_response, str) and not raw_response.startswith('{'):
                return raw_response
            return f"I encountered an error processing the email data: {str(e)}"
            
    except Exception as e:
        logger.error(f"Error in gmail_get_unread: {str(e)}")
        return f"I encountered an error while fetching your emails: {str(e)}"

# Map of function names to their implementations
FUNCTION_MAP = {
    'example_tool': example_tool,
    'calculator_tool': calculator_tool,
    'search_rules': search_rules,
    'get_unread_emails_json': get_unread_emails_json,
    'mark_email_as_read': mark_email_as_read,
    'mark_email_as_spam': mark_email_as_spam,
    'get_email_labels': get_email_labels,
    'create_email_label': create_email_label,
    'attach_label_to_email': attach_label_to_email,
    'gmail_get_unread': gmail_get_unread
}

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._initialize_db()
        self._register_default_tools()  # Register default tools on initialization

    def _initialize_db(self):
        """Initialize ChromaDB for tool storage."""
        try:
            persist_directory = os.path.join(os.path.dirname(__file__), "chroma_db")
            os.makedirs(persist_directory, exist_ok=True)
            
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(path=persist_directory)
            
            # Create or get collection for tools
            self.collection = self.client.get_or_create_collection(
                name="tools",
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("ChromaDB collection 'tools' initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {str(e)}")
            raise

    def _load_tools(self):
        """Load tools from ChromaDB into memory."""
        try:
            # Get all tools from ChromaDB
            results = self.collection.get()
            
            if results and results['ids']:
                for i, tool_id in enumerate(results['ids']):
                    tool_data = json.loads(results['metadatas'][i]['tool_data'])
                    
                    # Get the function from our function map
                    func_name = tool_data['func']
                    if func_name not in FUNCTION_MAP:
                        logger.warning(f"Function {func_name} not found in FUNCTION_MAP")
                        continue
                        
                    func = FUNCTION_MAP[func_name]
                    
                    # Get the schema class from our schema map
                    schema_name = tool_data.get('schema_name')
                    schema_class = SCHEMA_MAP.get(schema_name) if schema_name else None
                    
                    # Create the tool
                    tool = Tool.from_function(
                        func=func,
                        name=tool_data['name'],
                        description=tool_data['description'],
                        args_schema=schema_class
                    )
                    self._tools[tool.name] = tool
                logger.info(f"Loaded {len(results['ids'])} tools from ChromaDB")
            else:
                logger.info("No tools found in ChromaDB, initializing with default tools")
                self._register_default_tools()
                
        except Exception as e:
            logger.error(f"Failed to load tools from ChromaDB: {str(e)}")
            raise

    def _register_default_tools(self):
        """Register default tools and persist them to ChromaDB."""
        # Example tool registration
        self.register_tool(
            StructuredTool.from_function(
                func=example_tool,
                name="example_tool",
                description="An example tool that processes text.",
                args_schema=ExampleToolArgs
            )
        )

        # Gmail tools
        self.register_tool(
            StructuredTool.from_function(
                func=gmail_get_unread,
                name="gmail_unread",
                description="Get a natural summary of unread emails from Gmail inbox",
                args_schema=GetUnreadEmailsArgs,
                return_direct=False
            )
        )

        self.register_tool(
            StructuredTool.from_function(
                func=mark_email_as_read,
                name="gmail_mark_read",
                description="Mark a Gmail message as read using its message ID.",
                args_schema=MarkEmailArgs,
                return_direct=True
            )
        )

        self.register_tool(
            StructuredTool.from_function(
                func=mark_email_as_spam,
                name="gmail_mark_spam",
                description="Mark a Gmail message as spam using its message ID.",
                args_schema=MarkEmailArgs,
                return_direct=True
            )
        )

        self.register_tool(
            StructuredTool.from_function(
                func=get_email_labels,
                name="gmail_get_labels",
                description="Get all available Gmail labels",
                return_direct=False
            )
        )

        self.register_tool(
            StructuredTool.from_function(
                func=create_email_label,
                name="gmail_create_label",
                description="Create a new Gmail label with the specified name.",
                args_schema=CreateLabelArgs,
                return_direct=True
            )
        )

        self.register_tool(
            StructuredTool.from_function(
                func=attach_label_to_email,
                name="gmail_attach_label",
                description="Attach a Gmail label to a specific email. The message_id should be the Gmail message ID (usually a base64 string like 'a1b2c3d4') and not the email address format.",
                args_schema=AttachLabelArgs,
                return_direct=False
            )
        )

    def register_tool(self, tool: BaseTool) -> None:
        """Register a new tool in the registry and persist it to ChromaDB."""
        try:
            # Store in memory
            self._tools[tool.name] = tool
            
            # Get the function name from the function map
            func_name = None
            for name, func in FUNCTION_MAP.items():
                if func == tool.func:
                    func_name = name
                    break
            
            if not func_name:
                logger.warning(f"Could not find function name for tool {tool.name}")
                return
            
            # Get the schema name from our schema map
            schema_name = None
            if tool.args_schema:
                for name, schema in SCHEMA_MAP.items():
                    if schema == tool.args_schema:
                        schema_name = name
                        break
            
            # Prepare tool data for storage
            tool_data = {
                "name": tool.name,
                "description": tool.description,
                "func": func_name,  # Store function name instead of function reference
                "schema_name": schema_name,  # Store schema name instead of schema
                "args_schema": tool.args_schema.schema() if tool.args_schema else None
            }
            
            # Store in ChromaDB
            self.collection.add(
                ids=[tool.name],
                documents=[tool.description],
                metadatas=[{"tool_data": json.dumps(tool_data)}]
            )
            
            logger.info(f"Successfully registered and persisted tool: {tool.name}")
            
        except Exception as e:
            logger.error(f"Failed to register tool {tool.name}: {str(e)}")
            raise

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

    def unregister_tool(self, name: str) -> None:
        """Unregister a tool from the registry and remove it from ChromaDB."""
        try:
            if name in self._tools:
                # Remove from memory
                del self._tools[name]
                
                # Remove from ChromaDB
                self.collection.delete(ids=[name])
                
                logger.info(f"Successfully unregistered and removed tool: {name}")
            else:
                raise ValueError(f"Tool {name} not found")
                
        except Exception as e:
            logger.error(f"Failed to unregister tool {name}: {str(e)}")
            raise

# Create a global tool registry instance
tool_registry = ToolRegistry()

# Remove duplicate registrations since they are already registered in _register_default_tools
# The following code was removed:
# tool_registry.register_tool(
#     StructuredTool.from_function(
#         func=gmail_get_unread,
#         name="gmail_unread",
#         description="Get a natural summary of unread emails from Gmail inbox",
#         args_schema=GetUnreadEmailsArgs,
#         return_direct=False
#     )
# )
# 
# tool_registry.register_tool(
#     StructuredTool.from_function(
#         func=mark_email_as_read,
#         name="gmail_mark_read",
#         description="Mark a Gmail message as read using its message ID",
#         args_schema=MarkEmailArgs
#     )
# )
# 
# tool_registry.register_tool(
#     StructuredTool.from_function(
#         func=mark_email_as_spam,
#         name="gmail_mark_spam",
#         description="Mark a Gmail message as spam using its message ID",
#         args_schema=MarkEmailArgs
#     )
# )
# 
# tool_registry.register_tool(
#     StructuredTool.from_function(
#         func=get_email_labels,
#         name="gmail_get_labels",
#         description="Get all available Gmail labels",
#         return_direct=False
#     )
# )
# 
# tool_registry.register_tool(
#     StructuredTool.from_function(
#         func=create_email_label,
#         name="gmail_create_label",
#         description="Create a new Gmail label with the specified name",
#         args_schema=CreateLabelArgs
#     )
# )
# 
# tool_registry.register_tool(
#     StructuredTool.from_function(
#         func=attach_label_to_email,
#         name="gmail_attach_label",
#         description="Attach a Gmail label to a specific email. The message_id should be the Gmail message ID (usually a base64 string like 'a1b2c3d4') and not the email address format.",
#         args_schema=AttachLabelArgs,
#         return_direct=False
#     )
# ) 