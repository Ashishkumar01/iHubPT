import os
from typing import List, Dict, Any, Optional, Tuple
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.schema import Document
from app.models import Agent

class VectorStore:
    def __init__(self):
        self.persist_directory = os.path.join(os.path.dirname(__file__), "chroma_db")
        self.embeddings = OpenAIEmbeddings(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.vector_store = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embeddings,
            collection_name="agents"
        )

    def add_documents(self, documents: List[Document]) -> None:
        """Add documents to the vector store."""
        self.vector_store.add_documents(documents)

    def search(self, query: str, k: int = 4) -> List[Document]:
        """Search for similar documents."""
        return self.vector_store.similarity_search(query, k=k)

    def search_with_score(self, query: str, k: int = 4) -> List[Tuple[Document, float]]:
        """Search for similar documents with similarity scores."""
        return self.vector_store.similarity_search_with_score(query, k=k)

    def delete_collection(self, collection_name: str) -> None:
        """Delete a collection from the vector store."""
        self.vector_store.delete_collection(collection_name)

    def get_collection(self, collection_name: str) -> Optional[Chroma]:
        """Get a specific collection from the vector store."""
        return self.vector_store.get_collection(collection_name)

# Create a global vector store instance
vector_store = VectorStore() 