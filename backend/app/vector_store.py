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
        
        # Store the chat log
        self.chat_logs_collection.add(
            ids=[log_id],
            metadatas=[chat_log_data],
            documents=[f"{chat_log_data['request_message']}\n{chat_log_data['response_message']}"],
            embeddings=None  # Let Chroma compute embeddings
        )
        return log_id

    def get_chat_logs_by_agent(self, agent_id: str) -> List[Dict]:
        """Get all chat logs for a specific agent."""
        results = self.chat_logs_collection.get(
            where={"agent_id": agent_id}
        )
        return [metadata for metadata in results['metadatas']] if results['metadatas'] else []

    def get_chat_logs_by_timerange(self, start_time: str, end_time: str) -> List[Dict]:
        """Get chat logs within a specific time range."""
        # Convert timestamps to ISO format strings for comparison
        start_iso = datetime.fromisoformat(start_time.replace('Z', '+00:00')).isoformat()
        end_iso = datetime.fromisoformat(end_time.replace('Z', '+00:00')).isoformat()
        
        # Get all logs and filter in Python
        results = self.chat_logs_collection.get()
        if not results['metadatas']:
            return []
            
        # Filter logs within the time range
        filtered_logs = [
            metadata for metadata in results['metadatas']
            if start_iso <= metadata['timestamp'] <= end_iso
        ]
        return filtered_logs

    def get_token_usage_by_agent(self, agent_id: str) -> Dict:
        """Get token usage statistics for a specific agent."""
        logs = self.get_chat_logs_by_agent(agent_id)
        total_input = sum(log['input_tokens'] for log in logs)
        total_output = sum(log['output_tokens'] for log in logs)
        total = sum(log['total_tokens'] for log in logs)
        return {
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total,
            "total_interactions": len(logs)
        }

# Create a global vector store instance
vector_store = VectorStore() 