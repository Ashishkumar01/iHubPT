import os
import pickle
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_token(credentials_path, token_path):
    """Check if token is valid, expired, or missing and try to refresh if needed."""
    logger.info(f"Checking token at: {token_path}")
    
    if not os.path.exists(token_path):
        logger.error(f"Token file not found at: {token_path}")
        return False, "Token file not found"
    
    try:
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
            
        # Check token validity
        logger.info(f"Token loaded. Valid: {creds and creds.valid}, " 
                    f"Expired: {creds and creds.expired}, "
                    f"Has refresh token: {creds and creds.refresh_token is not None}")
        
        # If token is expired, try to refresh it
        if creds and creds.expired and creds.refresh_token:
            logger.info("Token expired. Attempting to refresh...")
            try:
                creds.refresh(Request())
                
                # Save the refreshed credentials
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
                    
                logger.info("Token refreshed successfully")
                return True, "Token refreshed successfully"
            except Exception as e:
                logger.error(f"Failed to refresh token: {str(e)}")
                return False, f"Failed to refresh token: {str(e)}"
        elif creds and creds.valid:
            logger.info("Token is valid")
            return True, "Token is valid"
        else:
            logger.error("Token is invalid and cannot be refreshed")
            return False, "Token is invalid and cannot be refreshed"
            
    except Exception as e:
        logger.error(f"Error checking token: {str(e)}")
        return False, f"Error checking token: {str(e)}"

if __name__ == "__main__":
    # Set paths to credentials and token
    base_dir = os.path.dirname(os.path.abspath(__file__))
    credentials_path = os.path.join(base_dir, 'credentials', 'google_credentials.json')
    token_path = os.path.join(base_dir, 'credentials', 'token.pickle')
    
    # Check if credentials file exists
    if not os.path.exists(credentials_path):
        logger.error(f"Credentials file not found at: {credentials_path}")
        exit(1)
        
    # Check token validity
    success, message = check_token(credentials_path, token_path)
    
    if success:
        print(f"SUCCESS: {message}")
    else:
        print(f"ERROR: {message}") 