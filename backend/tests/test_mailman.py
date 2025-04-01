import pytest
from app.mailman import get_gmail_service

def test_gmail_authentication():
    """Test Gmail authentication and token storage."""
    # Get the Gmail service
    service, error = get_gmail_service()
    
    # If there's an error, fail the test
    assert error is None, f"Authentication failed: {error}"
    
    # If we get here, we have a valid service
    assert service is not None, "Service should not be None"
    
    # Try to list messages to verify the service works
    try:
        results = service.users().messages().list(userId='me').execute()
        messages = results.get('messages', [])
        print(f"Successfully authenticated! Found {len(messages)} messages.")
    except Exception as e:
        pytest.fail(f"Failed to list messages: {str(e)}") 