import os
import sys
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.mailman import get_gmail_service

def main():
    print("Starting Gmail authentication process...")
    
    # Get the Gmail service
    service, error = get_gmail_service()
    
    if error:
        print(f"Authentication failed: {error}")
        return
    
    if service is None:
        print("Failed to get Gmail service")
        return
    
    try:
        # Try to list messages to verify the service works
        results = service.users().messages().list(userId='me').execute()
        messages = results.get('messages', [])
        print(f"\nAuthentication successful! 🎉")
        print(f"Found {len(messages)} messages in your inbox.")
        print("\nToken has been stored successfully for future use.")
        
    except Exception as e:
        print(f"Error while testing the service: {str(e)}")

if __name__ == "__main__":
    main() 