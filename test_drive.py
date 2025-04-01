from backend.app.drive_service import DocumentStoreService
import os
from pathlib import Path
from datetime import datetime

def test_create_file(doc_service):
    print('\n1. Testing create_file...')
    test_content = f'This is a test file created at {datetime.now().isoformat()}'
    file, error = doc_service.create_file('test_file_1.txt', test_content)
    if error:
        print(f'Error: {error}')
    else:
        print('Success! File created:')
        print(f'- Name: {file["name"]}')
        print(f'- ID: {file["id"]}')
        print(f'- Type: {file["mimeType"]}')
        print(f'- Created: {file["createdTime"]}')
        return file["id"]  # Return file ID for further testing
    return None

def test_search_files(doc_service):
    print('\n2. Testing search_files...')
    files, error = doc_service.search_files("mimeType = 'text/plain'", max_results=5)
    if error:
        print(f'Error: {error}')
    else:
        print('Success! Found files:')
        for file in files:
            print(f'- {file["name"]} (ID: {file["id"]}, Type: {file["mimeType"]})')

def test_get_file_content(doc_service, file_id):
    print('\n3. Testing get_file_content...')
    if not file_id:
        print('Skipping test: No file ID provided')
        return
    
    content, error = doc_service.get_file_content(file_id)
    if error:
        print(f'Error: {error}')
    else:
        print('Success! File content:')
        print(content)

def test_find_file_by_name(doc_service):
    print('\n4. Testing find_file_by_name...')
    file, error = doc_service.find_file_by_name('test_file_1.txt')
    if error:
        print(f'Error: {error}')
    else:
        print('Success! Found file:')
        print(f'- Name: {file["name"]}')
        print(f'- ID: {file["id"]}')
        print(f'- Type: {file["mimeType"]}')

def main():
    credentials_path = 'backend/credentials/google_credentials.json'
    print(f'Initializing DocumentStoreService with credentials from: {credentials_path}')
    doc_service = DocumentStoreService(credentials_path)
    
    # Run all tests
    file_id = test_create_file(doc_service)
    test_search_files(doc_service)
    test_get_file_content(doc_service, file_id)
    test_find_file_by_name(doc_service)

if __name__ == '__main__':
    main() 