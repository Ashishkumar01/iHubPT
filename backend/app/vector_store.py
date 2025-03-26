from typing import List, Optional
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document
import os

class VectorStore:
    def __init__(self):
        # Use the global OpenAI API key from environment
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        self.vector_store = Chroma(
            persist_directory="./data/chroma",
            embedding_function=self.embeddings
        )

    def add_documents(self, documents: List[Document]) -> None:
        """Add documents to the vector store."""
        self.vector_store.add_documents(documents)

    def search(self, query: str, k: int = 4) -> List[Document]:
        """Search for similar documents."""
        return self.vector_store.similarity_search(query, k=k)

    def search_with_score(self, query: str, k: int = 4) -> List[tuple[Document, float]]:
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