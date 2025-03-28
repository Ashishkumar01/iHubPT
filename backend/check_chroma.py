import chromadb
import os
import json

def check_chroma_contents():
    # Initialize ChromaDB client with the same path as in the engine
    persist_directory = os.path.join(os.path.dirname(__file__), "app", "chroma_db")
    client = chromadb.PersistentClient(path=persist_directory)
    
    # Get the agents collection
    collection = client.get_collection("agents")
    
    # Get all documents
    results = collection.get()
    
    print("\n=== ChromaDB Contents ===")
    print(f"Number of documents: {len(results['ids'])}")
    print("\nDocuments:")
    
    for idx, (doc_id, metadata, document) in enumerate(zip(results["ids"], results["metadatas"], results["documents"])):
        print(f"\n--- Document {idx + 1} ---")
        print(f"ID: {doc_id}")
        print("Metadata:")
        for key, value in metadata.items():
            print(f"  {key}: {value}")
        print(f"Description: {document}")

if __name__ == "__main__":
    check_chroma_contents() 