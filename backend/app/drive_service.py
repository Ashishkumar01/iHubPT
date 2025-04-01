from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import os
import io
import pickle
from pathlib import Path
import logging
from typing import Optional, Tuple, List, Dict, Any
import tempfile

logger = logging.getLogger(__name__)

class DriveService:
    """Service class for Google Drive operations."""
    
    SCOPES = [
        # Gmail Scopes
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify',
        'https://www.googleapis.com/auth/gmail.labels',
        # Drive Scopes
        'https://www.googleapis.com/auth/drive.metadata.readonly',
        'https://www.googleapis.com/auth/drive.file',
        'https://www.googleapis.com/auth/drive'
    ]
    
    def __init__(self, credentials_path: str):
        """
        Initialize the Drive service with credentials.
        
        Args:
            credentials_path (str): Path to the credentials JSON file
        """
        self.credentials_path = credentials_path
        self.token_path = os.path.join(os.path.dirname(credentials_path), 'token.pickle')
        self.service = None
    
    def get_service(self):
        """
        Get an authorized Drive service instance.
        
        Returns:
            Tuple[object, str]: (service object, error message if any)
        """
        try:
            creds = None
            # Load existing token if it exists
            if os.path.exists(self.token_path):
                with open(self.token_path, 'rb') as token:
                    creds = pickle.load(token)
            
            # If no valid credentials available, let user log in
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, self.SCOPES)
                    creds = flow.run_local_server(port=0)
                
                # Save the credentials for the next run
                with open(self.token_path, 'wb') as token:
                    pickle.dump(creds, token)
            
            # Build and return the Drive service
            self.service = build('drive', 'v3', credentials=creds)
            return self.service, None
            
        except Exception as e:
            error_msg = f"Error initializing Drive service: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
    
    def list_files(self, max_results: int = 10):
        """
        List files from Google Drive.
        
        Args:
            max_results (int): Maximum number of files to return
            
        Returns:
            Tuple[list, str]: (list of files, error message if any)
        """
        try:
            if not self.service:
                self.service, error = self.get_service()
                if error:
                    return [], error
            
            results = self.service.files().list(
                pageSize=max_results,
                fields="nextPageToken, files(id, name, mimeType, createdTime)"
            ).execute()
            
            files = results.get('files', [])
            return files, None
            
        except Exception as e:
            error_msg = f"Error listing files: {str(e)}"
            logger.error(error_msg)
            return [], error_msg

class DocumentStoreService:
    """Service class for Google Drive document operations."""
    
    def __init__(self, credentials_path: str):
        """Initialize with the same credentials as DriveService."""
        self.drive_service = DriveService(credentials_path)
        self.service = None
    
    def _ensure_service(self) -> Tuple[bool, Optional[str]]:
        """Ensure we have an active service connection."""
        if not self.service:
            service, error = self.drive_service.get_service()
            if error:
                return False, error
            self.service = service
        return True, None

    def search_files(self, query: str, max_results: int = 10) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Search for files in Google Drive using a query string.
        
        Args:
            query (str): Search query (follows Google Drive search syntax)
            max_results (int): Maximum number of results to return
            
        Returns:
            Tuple[List[Dict], Optional[str]]: (list of files, error message if any)
        """
        try:
            success, error = self._ensure_service()
            if not success:
                return [], error
            
            results = self.service.files().list(
                q=query,
                pageSize=max_results,
                fields="files(id, name, mimeType, createdTime, modifiedTime, size)",
                orderBy="modifiedTime desc"
            ).execute()
            
            return results.get('files', []), None
            
        except Exception as e:
            error_msg = f"Error searching files: {str(e)}"
            logger.error(error_msg)
            return [], error_msg

    def get_file_content(self, file_id: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Fetch and read the content of a file from Google Drive.
        
        Args:
            file_id (str): The ID of the file to read
            
        Returns:
            Tuple[Optional[str], Optional[str]]: (file content, error message if any)
        """
        try:
            success, error = self._ensure_service()
            if not success:
                return None, error
            
            # Get the file metadata first
            file = self.service.files().get(fileId=file_id, fields="mimeType").execute()
            
            # Download the file content
            request = self.service.files().get_media(fileId=file_id)
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            
            done = False
            while not done:
                _, done = downloader.next_chunk()
            
            content = file_content.getvalue().decode('utf-8')
            return content, None
            
        except Exception as e:
            error_msg = f"Error getting file content: {str(e)}"
            logger.error(error_msg)
            return None, error_msg

    def create_file(self, name: str, content: str, mime_type: str = 'text/plain') -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Create a new file in Google Drive.
        
        Args:
            name (str): Name of the file
            content (str): Content to write to the file
            mime_type (str): MIME type of the file (default: text/plain)
            
        Returns:
            Tuple[Optional[Dict], Optional[str]]: (file metadata, error message if any)
        """
        try:
            success, error = self._ensure_service()
            if not success:
                return None, error
            
            # Create file metadata
            file_metadata = {
                'name': name,
                'mimeType': mime_type
            }
            
            # Create a temporary file
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            try:
                # Create media content
                media = MediaFileUpload(
                    temp_file_path,
                    mimetype=mime_type,
                    resumable=True
                )
                
                # Create the file
                file = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id, name, mimeType, createdTime, modifiedTime, size'
                ).execute()
                
                return file, None
            finally:
                # Clean up temporary file
                os.unlink(temp_file_path)
                
        except Exception as e:
            error_msg = f"Error creating file: {str(e)}"
            logger.error(error_msg)
            return None, error_msg

    def find_file_by_name(self, name: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Find a file by its exact name.
        
        Args:
            name (str): The exact name of the file to find
            
        Returns:
            Tuple[Optional[Dict], Optional[str]]: (file metadata if found, error message if any)
        """
        try:
            # Search for files with the exact name
            query = f"name = '{name}'"
            files, error = self.search_files(query, max_results=1)
            
            if error:
                return None, error
                
            if not files:
                return None, f"No file found with name: {name}"
                
            return files[0], None
            
        except Exception as e:
            error_msg = f"Error finding file: {str(e)}"
            logger.error(error_msg)
            return None, error_msg

if __name__ == "__main__":
    # Test the Document Store Service
    credentials_path = os.path.join(Path(__file__).parent.parent, 'credentials', 'google_credentials.json')
    doc_service = DocumentStoreService(credentials_path)
    
    print("Testing Document Store Service...")
    
    # Test file creation
    print("\nCreating a test file...")
    test_content = "This is a test document created by DocumentStoreService"
    file, error = doc_service.create_file("test_document.txt", test_content)
    if error:
        print(f"Error creating file: {error}")
    else:
        print(f"Created file: {file['name']} (ID: {file['id']})")
        
        # Test file search
        print("\nSearching for text files...")
        files, error = doc_service.search_files("mimeType = 'text/plain'", max_results=5)
        if error:
            print(f"Error searching files: {error}")
        else:
            print("Found files:")
            for f in files:
                print(f"- {f['name']} ({f['id']})")
        
        # Test content retrieval
        print("\nRetrieving file content...")
        content, error = doc_service.get_file_content(file['id'])
        if error:
            print(f"Error getting content: {error}")
        else:
            print(f"File content: {content}")
        
        # Test find by name
        print("\nFinding file by name...")
        found_file, error = doc_service.find_file_by_name("test_document.txt")
        if error:
            print(f"Error finding file: {error}")
        else:
            print(f"Found file: {found_file['name']} (ID: {found_file['id']})")

    # Test the Drive and Gmail services
    credentials_path = os.path.join(Path(__file__).parent.parent, 'credentials', 'google_credentials.json')
    service = DriveService(credentials_path)
    
    print("Testing Google Services access...")
    
    # Get credentials first
    _, error = service.get_service()
    if error:
        print(f"Error getting service: {error}")
        exit(1)
    
    # Test Drive access
    print("\nTesting Drive access:")
    files, error = service.list_files(max_results=5)
    if error:
        print(f"Drive Error: {error}")
    else:
        print("Drive files found:")
        for file in files:
            print(f"- {file['name']} ({file['id']})")
    
    # Test Gmail access
    print("\nTesting Gmail access:")
    try:
        creds = None
        if os.path.exists(service.token_path):
            with open(service.token_path, 'rb') as token:
                creds = pickle.load(token)
        
        gmail_service = build('gmail', 'v1', credentials=creds)
        results = gmail_service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
        print("Gmail labels found:")
        for label in labels:
            print(f"- {label['name']} ({label['id']})")
    except Exception as e:
        print(f"Gmail Error: {str(e)}") 