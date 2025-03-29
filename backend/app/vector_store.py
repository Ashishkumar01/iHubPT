import os
from typing import List, Dict, Any, Optional, Tuple
import chromadb
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.schema import Document
from app.models import Agent
import logging

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

# Create a global vector store instance
vector_store = VectorStore() 