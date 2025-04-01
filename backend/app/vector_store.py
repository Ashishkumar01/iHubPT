import os
from typing import List, Dict, Any, Optional, Tuple
import chromadb
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.schema import Document
from app.models import Agent
import logging
from chromadb.config import Settings
import json
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self):
        """Initialize the vector store with OpenAI embeddings."""
        try:
            self.persist_directory = os.path.join(os.path.dirname(__file__), "chroma_db")
            os.makedirs(self.persist_directory, exist_ok=True)
            
            # Initialize OpenAI embeddings
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable is not set")
            
            self.embeddings = OpenAIEmbeddings(
                api_key=api_key
            )

            # Initialize Chroma client
            self.client = chromadb.PersistentClient(path=self.persist_directory)
            
            # Initialize vector store
            self.vector_store = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings,
                collection_name="agents",
                client=self.client
            )

            # Initialize collections
            self.agents_collection = self.client.get_or_create_collection("agents")
            self.chat_logs_collection = self.client.get_or_create_collection("chat_logs")

            logger.info("Vector store initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing vector store: {str(e)}")
            raise

    def add_documents(self, documents: List[Document]) -> None:
        """Add documents to the vector store."""
        try:
            self.vector_store.add_documents(documents)
            logger.info(f"Added {len(documents)} documents to vector store")
        except Exception as e:
            logger.error(f"Error adding documents: {str(e)}")
            raise

    def search(self, query: str, k: int = 4) -> List[Document]:
        """Search for similar documents."""
        try:
            return self.vector_store.similarity_search(query, k=k)
        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
            raise

    def search_with_score(self, query: str, k: int = 4) -> List[Tuple[Document, float]]:
        """Search for similar documents with similarity scores."""
        try:
            return self.vector_store.similarity_search_with_score(query, k=k)
        except Exception as e:
            logger.error(f"Error searching documents with score: {str(e)}")
            raise

    def delete_collection(self, collection_name: str) -> None:
        """Delete a collection from the vector store."""
        try:
            self.client.delete_collection(collection_name)
            logger.info(f"Deleted collection: {collection_name}")
        except Exception as e:
            logger.error(f"Error deleting collection: {str(e)}")
            raise

    def get_collection(self, collection_name: str) -> Optional[chromadb.Collection]:
        """Get a specific collection from the vector store."""
        try:
            return self.client.get_collection(collection_name)
        except Exception as e:
            logger.error(f"Error getting collection: {str(e)}")
            return None

    def add_chat_log(self, chat_log_data: Dict) -> str:
        """Add a chat log to the collection."""
        log_id = str(uuid.uuid4())
        chat_log_data['id'] = log_id
        chat_log_data['timestamp'] = datetime.utcnow().isoformat()
        
        # Convert all values to strings to satisfy ChromaDB requirements
        string_metadata = {}
        for key, value in chat_log_data.items():
            if isinstance(value, (dict, list)):
                string_metadata[key] = json.dumps(value)
            else:
                string_metadata[key] = str(value)
        
        # Store the chat log
        self.chat_logs_collection.add(
            ids=[log_id],
            metadatas=[string_metadata],
            documents=[f"{chat_log_data['request_message']}\n{chat_log_data['response_message']}"],
            embeddings=None  # Let Chroma compute embeddings
        )
        return log_id

    def get_chat_logs_by_agent(self, agent_id: str) -> List[Dict]:
        """Get all chat logs for a specific agent."""
        results = self.chat_logs_collection.get(
            where={"agent_id": agent_id}
        )
        
        logs = []
        if results['metadatas']:
            for i, metadata in enumerate(results['metadatas']):
                # Add id from results['ids'] if available
                if 'ids' in results and i < len(results['ids']):
                    metadata['id'] = results['ids'][i]
                    
                # Add content from results['documents'] if available
                if 'documents' in results and i < len(results['documents']):
                    metadata['content'] = results['documents'][i]
                
                # Ensure metadata is a dictionary
                if isinstance(metadata.get('metadata'), str):
                    try:
                        metadata['metadata'] = json.loads(metadata['metadata'])
                    except json.JSONDecodeError:
                        metadata['metadata'] = {}
                elif metadata.get('metadata') is None:
                    metadata['metadata'] = {}
                
                # Set default values for missing fields required by ChatLog model
                metadata['user'] = metadata.get('requestor_id', 'Administrator')
                metadata['department'] = metadata.get('department', 'Post Trade')
                
                # Convert string numeric values to actual numbers
                try:
                    metadata['input_tokens'] = int(metadata.get('input_tokens', 0))
                    metadata['output_tokens'] = int(metadata.get('output_tokens', 0))
                    metadata['total_tokens'] = int(metadata.get('total_tokens', 0))
                    metadata['duration_ms'] = int(metadata.get('duration_ms', 0))
                    metadata['cost'] = float(metadata.get('cost', 0.0))
                    metadata['temperature'] = float(metadata.get('temperature', 0.0))
                except (ValueError, TypeError):
                    # Default to 0 if conversion fails
                    metadata['input_tokens'] = 0
                    metadata['output_tokens'] = 0
                    metadata['total_tokens'] = 0
                    metadata['duration_ms'] = 0
                    metadata['cost'] = 0.0
                    metadata['temperature'] = 0.0
                
                logs.append(metadata)
                
        return logs

    def get_chat_logs_by_timerange(self, start_time: str, end_time: str) -> List[Dict]:
        """Get chat logs within a specific time range."""
        # Convert timestamps to ISO format strings for comparison
        start_iso = datetime.fromisoformat(start_time.replace('Z', '+00:00')).isoformat()
        end_iso = datetime.fromisoformat(end_time.replace('Z', '+00:00')).isoformat()
        
        # Get all logs
        results = self.chat_logs_collection.get()
        if not results['metadatas']:
            return []
            
        # Filter logs within the time range and ensure metadata is properly formatted
        filtered_logs = []
        for i, metadata in enumerate(results['metadatas']):
            log_time = metadata.get('timestamp', '')
            if log_time and start_iso <= log_time <= end_iso:
                # Add id from results['ids'] if available
                if 'ids' in results and i < len(results['ids']):
                    metadata['id'] = results['ids'][i]
                    
                # Add content from results['documents'] if available
                if 'documents' in results and i < len(results['documents']):
                    metadata['content'] = results['documents'][i]
                
                # Ensure metadata is a dictionary
                if isinstance(metadata.get('metadata'), str):
                    try:
                        metadata['metadata'] = json.loads(metadata['metadata'])
                    except json.JSONDecodeError:
                        metadata['metadata'] = {}
                elif metadata.get('metadata') is None:
                    metadata['metadata'] = {}
                    
                # Set default values for missing fields required by ChatLog model
                metadata['user'] = metadata.get('requestor_id', 'Administrator')
                metadata['department'] = metadata.get('department', 'Post Trade')
                
                # Convert string numeric values to actual numbers
                try:
                    metadata['input_tokens'] = int(metadata.get('input_tokens', '0'))
                    metadata['output_tokens'] = int(metadata.get('output_tokens', '0'))
                    metadata['total_tokens'] = int(metadata.get('total_tokens', '0'))
                    metadata['duration_ms'] = int(metadata.get('duration_ms', '0'))
                    
                    # Handle cost carefully
                    cost_str = metadata.get('cost', '0.0')
                    if cost_str and cost_str != 'none':
                        metadata['cost'] = float(cost_str)
                    else:
                        metadata['cost'] = 0.0
                        
                    # Handle temperature carefully
                    temp_str = metadata.get('temperature', '0.0')
                    if temp_str and temp_str != 'none':
                        metadata['temperature'] = float(temp_str)
                    else:
                        metadata['temperature'] = 0.0
                        
                except (ValueError, TypeError) as e:
                    # Log the error
                    logger.warning(f"Error converting numeric values in metadata: {str(e)}")
                    logger.debug(f"Problematic metadata: {metadata}")
                    
                    # Default to 0 if conversion fails
                    metadata['input_tokens'] = 0
                    metadata['output_tokens'] = 0
                    metadata['total_tokens'] = 0
                    metadata['duration_ms'] = 0
                    metadata['cost'] = 0.0
                    metadata['temperature'] = 0.0
                
                filtered_logs.append(metadata)
                
        return filtered_logs

    def get_token_usage_by_agent(self, agent_id: str) -> Dict:
        """Get token usage statistics for a specific agent."""
        logs = self.get_chat_logs_by_agent(agent_id)
        
        # Safely parse and sum up token usage, handling different data types
        total_input = 0
        total_output = 0
        total = 0
        total_cost = 0.0
        
        for log in logs:
            try:
                # Try to parse token values
                input_tokens = int(log.get('input_tokens', '0'))
                output_tokens = int(log.get('output_tokens', '0'))
                total_tokens = int(log.get('total_tokens', '0'))
                
                # Try to parse cost
                cost_str = log.get('cost', '0.0')
                cost = float(cost_str) if cost_str and cost_str != 'none' else 0.0
                
                # Add to totals
                total_input += input_tokens
                total_output += output_tokens
                total += total_tokens
                total_cost += cost
                
            except (ValueError, TypeError) as e:
                # Log the error but continue processing
                logger.warning(f"Error parsing token values in log: {str(e)}")
                logger.debug(f"Problematic log entry: {log}")
        
        return {
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total,
            "total_cost": round(total_cost, 6),
            "total_interactions": len(logs)
        }

    def get_chat_logs_by_agent_and_timerange(self, agent_id: str, start_time: str, end_time: str) -> List[Dict]:
        """Get chat logs for a specific agent within a specific time range."""
        # Convert timestamps to ISO format strings for comparison
        start_iso = datetime.fromisoformat(start_time.replace('Z', '+00:00')).isoformat()
        end_iso = datetime.fromisoformat(end_time.replace('Z', '+00:00')).isoformat()
        
        # Get all logs for the agent
        results = self.chat_logs_collection.get(
            where={"agent_id": agent_id}
        )
        
        if not results['metadatas']:
            return []
            
        # Filter logs within the time range and ensure metadata is properly formatted
        filtered_logs = []
        for i, metadata in enumerate(results['metadatas']):
            log_time = metadata.get('timestamp', '')
            if log_time and start_iso <= log_time <= end_iso:
                # Add id from results['ids'] if available
                if 'ids' in results and i < len(results['ids']):
                    metadata['id'] = results['ids'][i]
                    
                # Add content from results['documents'] if available
                if 'documents' in results and i < len(results['documents']):
                    metadata['content'] = results['documents'][i]
                
                # Ensure metadata is a dictionary
                if isinstance(metadata.get('metadata'), str):
                    try:
                        metadata['metadata'] = json.loads(metadata['metadata'])
                    except json.JSONDecodeError:
                        metadata['metadata'] = {}
                elif metadata.get('metadata') is None:
                    metadata['metadata'] = {}
                    
                # Set default values for missing fields required by ChatLog model
                metadata['user'] = metadata.get('requestor_id', 'Administrator')
                metadata['department'] = metadata.get('department', 'Post Trade')
                
                # Convert string numeric values to actual numbers
                try:
                    metadata['input_tokens'] = int(metadata.get('input_tokens', '0'))
                    metadata['output_tokens'] = int(metadata.get('output_tokens', '0'))
                    metadata['total_tokens'] = int(metadata.get('total_tokens', '0'))
                    metadata['duration_ms'] = int(metadata.get('duration_ms', '0'))
                    
                    # Handle cost carefully
                    cost_str = metadata.get('cost', '0.0')
                    if cost_str and cost_str != 'none':
                        metadata['cost'] = float(cost_str)
                    else:
                        metadata['cost'] = 0.0
                        
                    # Handle temperature carefully
                    temp_str = metadata.get('temperature', '0.0')
                    if temp_str and temp_str != 'none':
                        metadata['temperature'] = float(temp_str)
                    else:
                        metadata['temperature'] = 0.0
                        
                except (ValueError, TypeError) as e:
                    # Log the error
                    logger.warning(f"Error converting numeric values in metadata: {str(e)}")
                    logger.debug(f"Problematic metadata: {metadata}")
                    
                    # Default to 0 if conversion fails
                    metadata['input_tokens'] = 0
                    metadata['output_tokens'] = 0
                    metadata['total_tokens'] = 0
                    metadata['duration_ms'] = 0
                    metadata['cost'] = 0.0
                    metadata['temperature'] = 0.0
                
                filtered_logs.append(metadata)
                
        return filtered_logs

# Create a global vector store instance
vector_store = VectorStore() 