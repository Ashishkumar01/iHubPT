import pytest
from fastapi import status

def test_add_documents(client):
    documents = [
        {
            "content": "Test document 1",
            "metadata": {"source": "test"}
        },
        {
            "content": "Test document 2",
            "metadata": {"source": "test"}
        }
    ]
    
    response = client.post("/api/v1/vector-store/add", json={"documents": documents})
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "success"
    assert data["message"] == "Added 2 documents"

def test_add_documents_invalid_data(client):
    response = client.post("/api/v1/vector-store/add", json={})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_search_documents(client):
    # Add a test document first
    documents = [
        {
            "content": "Test document for search",
            "metadata": {"source": "test"}
        }
    ]
    client.post("/api/v1/vector-store/add", json={"documents": documents})
    
    # Search for the document
    response = client.post("/api/v1/vector-store/search", json={"query": "test document"})
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["content"] == "Test document for search"

def test_search_documents_empty_query(client):
    response = client.post("/api/v1/vector-store/search", json={"query": ""})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_search_documents_no_results(client):
    response = client.post("/api/v1/vector-store/search", json={"query": "nonexistent content"})
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0

def test_delete_documents(client):
    # Add a test document first
    documents = [
        {
            "content": "Test document for deletion",
            "metadata": {"source": "test"}
        }
    ]
    client.post("/api/v1/vector-store/add", json={"documents": documents})
    
    # Delete the document
    response = client.post("/api/v1/vector-store/delete", json={"query": "test document for deletion"})
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "success"
    assert "deleted" in data["message"].lower()
    
    # Verify the document is deleted
    search_response = client.post("/api/v1/vector-store/search", json={"query": "test document for deletion"})
    assert search_response.status_code == status.HTTP_200_OK
    search_data = search_response.json()
    assert len(search_data) == 0

def test_delete_documents_empty_query(client):
    response = client.post("/api/v1/vector-store/delete", json={"query": ""})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_delete_documents_no_matches(client):
    response = client.post("/api/v1/vector-store/delete", json={"query": "nonexistent content"})
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "success"
    assert "no documents" in data["message"].lower() 