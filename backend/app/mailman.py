import os
import pickle
import logging
import base64
import json
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any, Union
from datetime import datetime
from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup
import re

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configure logging
logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify'
]

class GmailService:
    def __init__(self, credentials_path: str):
        """
        Initialize Gmail service with credentials path.
        
        Args:
            credentials_path (str): Path to the client secrets JSON file
        """
        self.credentials_path = credentials_path
        token_dir = os.path.dirname(credentials_path)
        self.token_path = os.path.join(token_dir, 'token.pickle')
        self.service = None
        self.creds = None
        
        logger.info(f"Initializing GmailService with credentials: {credentials_path}")
        logger.info(f"Token path: {self.token_path}")

    def _get_credentials(self) -> Optional[Credentials]:
        """
        Get valid user credentials from storage.
        
        Returns:
            Optional[Credentials]: The user credentials if valid, None otherwise
        """
        try:
            logger.info(f"Checking for token at: {self.token_path}")
            if os.path.exists(self.token_path):
                logger.info("Token file found, loading credentials...")
                with open(self.token_path, 'rb') as token:
                    self.creds = pickle.load(token)
                    logger.info(f"Token loaded. Valid: {self.creds and self.creds.valid}, " 
                                f"Expired: {self.creds and self.creds.expired}, "
                                f"Has refresh token: {self.creds and self.creds.refresh_token is not None}")

            # If there are no (valid) credentials available, let the user log in.
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    logger.info("Refreshing expired token...")
                    self.creds.refresh(Request())
                    logger.info("Token refreshed successfully")
                else:
                    logger.info(f"Need to generate new credentials from client secret: {self.credentials_path}")
                    if not os.path.exists(self.credentials_path):
                        logger.error(f"Credentials file not found at: {self.credentials_path}")
                        return None
                        
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES)
                    self.creds = flow.run_local_server(port=0)
                    logger.info("New credentials obtained successfully")
                
                # Save the credentials for the next run
                logger.info(f"Saving credentials to: {self.token_path}")
                with open(self.token_path, 'wb') as token:
                    pickle.dump(self.creds, token)

            return self.creds

        except Exception as e:
            logger.error(f"Error getting credentials: {str(e)}")
            return None

    def get_service(self) -> Tuple[Optional[object], Optional[str]]:
        """
        Get or create Gmail API service.
        
        Returns:
            Tuple[Optional[object], Optional[str]]: 
                - The Gmail service object if successful, None otherwise
                - Error message if failed, None if successful
        """
        try:
            self.creds = self._get_credentials()
            if not self.creds:
                return None, "Failed to get valid credentials"

            self.service = build('gmail', 'v1', credentials=self.creds)
            return self.service, None

        except HttpError as error:
            error_msg = f"An error occurred: {error}"
            logger.error(error_msg)
            return None, error_msg
        except Exception as e:
            error_msg = f"An unexpected error occurred: {str(e)}"
            logger.error(error_msg)
            return None, error_msg

    def _get_email_content(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract email content from a message.
        
        Args:
            message (Dict[str, Any]): The message object from Gmail API
            
        Returns:
            Dict[str, Any]: Dictionary containing email details
        """
        headers = message['payload']['headers']
        
        # Extract all relevant headers
        header_map = {h['name'].lower(): h['value'] for h in headers}
        
        # Get email body
        body = ""
        html_body = ""
        attachments = []
        
        if 'parts' in message['payload']:
            for part in message['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                elif part['mimeType'] == 'text/html':
                    if 'data' in part['body']:
                        html_body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                elif part['mimeType'].startswith('application/'):
                    # Handle attachments
                    attachment = {
                        'filename': part.get('filename', ''),
                        'mimeType': part['mimeType'],
                        'size': part['body'].get('size', 0)
                    }
                    attachments.append(attachment)
        elif 'body' in message['payload'] and 'data' in message['payload']['body']:
            body = base64.urlsafe_b64decode(message['payload']['body']['data']).decode('utf-8')
        
        # Parse date string to datetime object
        date_str = header_map.get('date', '')
        try:
            date = parsedate_to_datetime(date_str)
        except:
            date = None
        
        return {
            'id': message['id'],
            'threadId': message['threadId'],
            'labels': message.get('labelIds', []),
            'subject': header_map.get('subject', ''),
            'sender': {
                'name': header_map.get('from', ''),
                'email': header_map.get('from', '').split('<')[-1].rstrip('>')
            },
            'recipients': {
                'to': header_map.get('to', ''),
                'cc': header_map.get('cc', ''),
                'bcc': header_map.get('bcc', '')
            },
            'date': {
                'raw': date_str,
                'parsed': date.isoformat() if date else None
            },
            'content': {
                'plain': body,
                'html': html_body
            },
            'attachments': attachments,
            'snippet': message.get('snippet', '')
        }

    def get_unread_emails(self, max_results: int = 10) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Fetch unread emails from Gmail.
        
        Args:
            max_results (int): Maximum number of emails to fetch
            
        Returns:
            Tuple[Optional[Dict[str, Any]], Optional[str]]: 
                - Dictionary containing email list and metadata if successful, None otherwise
                - Error message if failed, None if successful
        """
        try:
            if not self.service:
                service, error = self.get_service()
                if error:
                    return None, error
                self.service = service

            # Query for unread messages
            results = self.service.users().messages().list(
                userId='me',
                labelIds=['UNREAD'],
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])
            if not messages:
                return {
                    'emails': [],
                    'metadata': {
                        'total': 0,
                        'fetched': 0,
                        'timestamp': datetime.now().isoformat()
                    }
                }, None

            # Get full message details
            emails = []
            for message in messages:
                msg = self.service.users().messages().get(
                    userId='me',
                    id=message['id'],
                    format='full'
                ).execute()
                
                email_content = self._get_email_content(msg)
                emails.append(email_content)

            return {
                'emails': emails,
                'metadata': {
                    'total': len(messages),
                    'fetched': len(emails),
                    'timestamp': datetime.now().isoformat()
                }
            }, None

        except HttpError as error:
            error_msg = f"An error occurred: {error}"
            logger.error(error_msg)
            return None, error_msg
        except Exception as e:
            error_msg = f"An unexpected error occurred: {str(e)}"
            logger.error(error_msg)
            return None, error_msg

    def revoke_credentials(self) -> bool:
        """
        Revoke the current credentials and delete the token file.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if self.creds:
                self.creds.revoke(Request())
            
            if os.path.exists(self.token_path):
                os.remove(self.token_path)
            
            self.creds = None
            self.service = None
            return True
        except Exception as e:
            logger.error(f"Error revoking credentials: {str(e)}")
            return False

    def mark_as_read(self, message_id: str) -> Tuple[bool, Optional[str]]:
        """
        Mark an email as read.
        
        Args:
            message_id (str): The ID of the message to mark as read
            
        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            return True, None
        except Exception as e:
            logger.error(f"Error marking message {message_id} as read: {str(e)}")
            return False, str(e)

    def mark_as_spam(self, message_id: str) -> Tuple[bool, Optional[str]]:
        """
        Mark an email as spam.
        
        Args:
            message_id (str): The ID of the message to mark as spam
            
        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': ['SPAM']}
            ).execute()
            return True, None
        except Exception as e:
            logger.error(f"Error marking message {message_id} as spam: {str(e)}")
            return False, str(e)

    def read_labels(self) -> Tuple[List[Dict[str, str]], Optional[str]]:
        """
        Get all available email labels.
        
        Returns:
            Tuple[List[Dict[str, str]], Optional[str]]: (list of labels with name and id, error_message)
        """
        try:
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            return [{'id': label['id'], 'name': label['name']} for label in labels], None
        except Exception as e:
            logger.error(f"Error reading labels: {str(e)}")
            return [], str(e)

    def create_label(self, label_name: str) -> Tuple[Dict[str, str], Optional[str]]:
        """
        Create a new label.
        
        Args:
            label_name (str): Name of the label to create
            
        Returns:
            Tuple[Dict[str, str], Optional[str]]: (created label info, error_message)
        """
        try:
            label_object = {
                'name': label_name,
                'messageListVisibility': 'show',
                'labelListVisibility': 'labelShow'
            }
            created_label = self.service.users().labels().create(
                userId='me',
                body=label_object
            ).execute()
            return {
                'id': created_label['id'],
                'name': created_label['name']
            }, None
        except Exception as e:
            logger.error(f"Error creating label {label_name}: {str(e)}")
            return {}, str(e)

    def attach_label_to_email(self, message_id: str, label_id: str) -> Tuple[bool, Optional[str]]:
        """
        Attach a label to an email.
        
        Args:
            message_id (str): The ID of the message to label
            label_id (str): The ID or name of the label to attach
            
        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        try:
            # Clean and validate the message ID
            clean_message_id = extract_message_id(message_id)
            
            # Get credentials path and create service
            credentials_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'credentials', 'google_credentials.json')
            gmail_service = GmailService(credentials_path)
            
            # Get service
            service, error = gmail_service.get_service()
            if error:
                return False, error
            
            # Check if label_id is actually a label name and convert it to ID if necessary
            actual_label_id = label_id
            if not label_id.startswith("LABEL_") and not label_id in ["INBOX", "SENT", "DRAFT", "TRASH", "SPAM", "UNREAD", "STARRED", "IMPORTANT"]:
                # This looks like a label name, not an ID - get the actual ID
                labels, error = gmail_service.read_labels()
                if error:
                    return False, f"Error reading labels: {error}"
                
                # Look for the label by name
                label_found = False
                for label in labels:
                    if label['name'].lower() == label_id.lower():
                        actual_label_id = label['id']
                        label_found = True
                        logger.info(f"Converted label name '{label_id}' to ID '{actual_label_id}'")
                        break
                
                if not label_found:
                    return False, f"Label '{label_id}' not found. Please create it first or check the name."
            
            # Instead of recursively calling attach_label_to_email, use service directly
            try:
                service.users().messages().modify(
                    userId='me',
                    id=clean_message_id,
                    body={'addLabelIds': [actual_label_id]}
                ).execute()
                success = True
                error = None
            except Exception as e:
                success = False
                error = str(e)
                logger.error(f"Error attaching label {actual_label_id} to message {clean_message_id}: {error}")
            
            if not success and error and ("Invalid id value" in error or "Invalid message_id" in error):
                # Provide more helpful error message
                return False, f"Invalid Gmail message ID format: {message_id}. Please use the actual Gmail message ID, not the email address."
            
            return True, None
            
        except Exception as e:
            error_msg = f"An error occurred: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

def get_gmail_service() -> Tuple[Optional[object], Optional[str]]:
    """Get the Gmail service from the service account credentials."""
    try:
        # Create a GmailService instance with path to credentials
        credentials_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'credentials', 'google_credentials.json')
        gmail_service = GmailService(credentials_path)
        service, error = gmail_service.get_service()
        return service, error
    except Exception as e:
        error_msg = f"Error getting Gmail service: {str(e)}"
        logger.error(error_msg)
        return None, error_msg

def clean_html_content(html_content: str) -> str:
    """Clean and extract readable text from HTML content."""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
            
        # Remove hidden elements
        for hidden in soup.find_all(style=lambda value: value and "display:none" in value):
            hidden.decompose()
            
        # Handle common email quote markers
        quotes = soup.find_all(class_=lambda x: x and any(quote in x.lower() for quote in [
            'quote', 'gmail_quote', 'yahoo_quoted', 'outlook_quote'
        ]))
        for quote in quotes:
            quote.decompose()
            
        # Extract text with better formatting
        lines = []
        for element in soup.descendants:
            if isinstance(element, str) and element.strip():
                lines.append(element.strip())
            elif element.name in ['br', 'p', 'div', 'tr', 'li']:
                lines.append('\n')
                
        # Clean up the text
        text = ' '.join(lines)
        text = '\n'.join(line.strip() for line in text.splitlines() if line.strip())
        
        return text.strip()
    except Exception as e:
        logger.error(f"Error cleaning HTML content: {str(e)}")
        return html_content

def extract_email_content(email_data: Dict[str, Any]) -> str:
    """Extract and clean email content from various formats."""
    try:
        # Check if the email_data has content directly
        if "content" in email_data:
            # If we already have processed content, use it
            if isinstance(email_data["content"], str) and email_data["content"].strip():
                return email_data["content"].strip()
            
        # Try to get content from both plain text and HTML parts
        plain_text = email_data.get("content", {}).get("plain", "")
        html_content = email_data.get("content", {}).get("html", "")
            
        # Prefer plain text if available
        if plain_text and isinstance(plain_text, str):
            return clean_text_content(plain_text)
        # Otherwise, clean HTML content
        elif html_content and isinstance(html_content, str):
            return clean_html_content(html_content)
        
        # If no content is found in the expected places, use the snippet
        if email_data.get("snippet"):
            return clean_text_content(email_data["snippet"])
            
        # If we still don't have content, return empty string
        return ""
            
    except Exception as e:
        logger.error(f"Error extracting email content: {str(e)}")
        # In case of error, try to return any available text
        if isinstance(email_data, dict):
            for field in ["snippet", "subject"]:
                if field in email_data and email_data[field]:
                    return f"[Error extracting full content] {email_data[field]}"
        return "[Error extracting email content]"

def clean_text_content(text: str) -> str:
    """Clean plain text email content."""
    try:
        # Split into lines
        lines = text.splitlines()
        
        # Remove common signature markers and everything after them
        signature_markers = [
            "Thanks and Regards,",
            "Best regards,",
            "Regards,",
            "Thank you,",
            "Best,",
            "--",
            "Sent from my iPhone",
            "Sent from my mobile",
            "Get Outlook for"
        ]
        
        cleaned_lines = []
        for line in lines:
            if any(marker in line for marker in signature_markers):
                break
            cleaned_lines.append(line)
            
        # Remove quoted text (lines starting with >)
        cleaned_lines = [line for line in cleaned_lines if not line.strip().startswith('>')]
        
        # Remove empty lines at the start and end
        while cleaned_lines and not cleaned_lines[0].strip():
            cleaned_lines.pop(0)
        while cleaned_lines and not cleaned_lines[-1].strip():
            cleaned_lines.pop()
            
        # Join lines, preserving paragraphs
        text = '\n'.join(cleaned_lines)
        
        # Remove excessive whitespace
        text = ' '.join(text.split())
        
        # Clean up common email artifacts
        text = re.sub(r'On.*wrote:', '', text)  # Remove "On [date] [person] wrote:"
        text = re.sub(r'<[^>]+>', '', text)  # Remove any HTML tags that slipped through
        
        return text.strip()
        
    except Exception as e:
        logger.error(f"Error cleaning text content: {str(e)}")
        return text

def format_emails_conversationally(emails_data: Dict[str, Any]) -> str:
    """
    Format email data in a conversational, human-like way.
    
    Args:
        emails_data (Dict[str, Any]): Dictionary containing email list and metadata
        
    Returns:
        str: Conversational description of emails
    """
    # Handle case with no emails
    if not emails_data.get("emails"):
        return "You don't have any unread emails at the moment."
    
    emails = emails_data["emails"]
    email_count = len(emails)
    
    # Create simple summary for 1-5 emails
    if email_count == 1:
        email = emails[0]
        sender_name = email["sender"]["name"].split('<')[0].strip()
        subject = email["subject"]
        message_id = email["id"]  # Get the message ID
        
        response = f"You have 1 unread email.\n\n"
        response += "Here's a summary of your unread email:\n\n"
        response += f"- From: {sender_name}\n"
        response += f"- Subject: {subject}\n"
        response += f"- Message ID: {message_id}\n"  # Include message ID
        response += f"- Date: {email['date']}\n"
        
        # Add content snippet or full content depending on length
        content = email.get("content", "").strip()
        if len(content) > 300:
            content = content[:297] + "..."
        
        response += f"- Content: {content}\n\n"
        
        # Add suggested actions
        response += "Would you like me to help you:\n"
        response += "- Mark this email as read (use message ID: " + message_id + ")\n"
        response += "- Add labels to organize it (use message ID: " + message_id + ")\n"
        
        return response
    
    # Create categorical summary for multiple emails
    elif email_count > 1:
        response = f"You have {email_count} unread emails.\n\n"
        response += "Here's a summary of your unread emails:\n\n"
        
        # List all emails with basic info
        for i, email in enumerate(emails, 1):
            sender_name = email["sender"]["name"].split('<')[0].strip()
            subject = email["subject"]
            message_id = email["id"]  # Get the message ID
            response += f"{i}. From {sender_name} about '{subject}'\n"
            response += f"   Message ID: {message_id}\n"  # Include message ID on a separate line for clarity
        
        response += "\nWould you like me to help you:\n"
        response += "- Mark any of these emails as read (just provide the message ID)\n"
        response += "- Add labels to organize them (provide the message ID and label name)\n"
        
        return response
    
    else:
        return "You don't have any unread emails at the moment."

def get_unread_emails_json(max_results: int = 10) -> str:
    """
    Get unread emails from Gmail in JSON format.
    
    Args:
        max_results (int): Maximum number of emails to fetch
        
    Returns:
        str: JSON string with email data or error message
    """
    try:
        # Initialize Gmail service
        service, error = get_gmail_service()
        if error:
            logger.error(f"Error getting Gmail service: {error}")
            return json.dumps({
                "success": False,
                "error": error,
                "message": f"Error connecting to Gmail: {error}"
            })
        
        # Create service instance and fetch emails
        credentials_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'credentials', 'google_credentials.json')
        gmail = GmailService(credentials_path)
        
        # Check token validity
        token_path = os.path.join(os.path.dirname(credentials_path), 'token.pickle')
        if not os.path.exists(token_path):
            return json.dumps({
                "success": False,
                "error": "No valid token found",
                "message": "Please authenticate with Gmail first."
            })
        
        # Get emails
        emails_data, error = gmail.get_unread_emails(max_results)
        if error:
            return json.dumps({
                "success": False,
                "error": error,
                "message": f"Error fetching emails: {error}"
            })
        
        if not emails_data or not emails_data.get('emails'):
            logger.info("No unread emails found")
            return json.dumps({
                "success": True,
                "has_emails": False,
                "message": "You don't have any unread emails at the moment.",
                "emails": []
            })
        
        # Process and clean the email content
        formatted_emails = []
        for email in emails_data['emails']:
            # Extract clean content
            content = extract_email_content(email)
            
            # Format each email
            formatted_email = {
                "id": email["id"],  # Ensure message ID is included
                "sender": {
                    "name": email["sender"]["name"].split('<')[0].strip(),
                    "email": email["sender"]["email"]
                },
                "subject": email["subject"],
                "date": email["date"]["parsed"] or email["date"]["raw"],
                "snippet": clean_text_content(email["snippet"]),
                "content": content,
                "has_attachments": len(email["attachments"]) > 0,
                "labels": email["labels"],
                "importance": "High" if "IMPORTANT" in email["labels"] else "Normal"
            }
            formatted_emails.append(formatted_email)
        
        # Create a conversation-friendly response
        email_count = len(formatted_emails)
        logger.info(f"Found {email_count} unread emails")
        
        # Data for AI processing with the new format
        result = {
            "success": True,
            "has_emails": True,
            "count": email_count,
            "emails": formatted_emails,
            "metadata": emails_data.get("metadata", {})
        }
        
        # Add a human-readable message for the conversational part
        conversational_summary = format_emails_conversationally({"emails": formatted_emails, "metadata": emails_data.get("metadata", {})})
        result["message"] = conversational_summary
        
        return json.dumps(result)
        
    except Exception as e:
        logger.error(f"Error in get_unread_emails_json: {str(e)}")
        return json.dumps({
            "success": False, 
            "error": str(e),
            "message": f"An error occurred while retrieving your emails: {str(e)}"
        })

def mark_email_as_read(message_id: str) -> str:
    """
    Mark an email as read.
    
    Args:
        message_id (str): The ID of the message to mark as read
        
    Returns:
        str: JSON string with the result
    """
    try:
        # Get credentials path and create service
        credentials_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'credentials', 'google_credentials.json')
        gmail_service = GmailService(credentials_path)
        
        # Get service
        service, error = gmail_service.get_service()
        if error:
            return json.dumps({"success": False, "error": error})
        
        # Mark as read
        success, error = gmail_service.mark_as_read(message_id)
        return json.dumps({
            "success": success,
            "error": error,
            "message": "Email marked as read" if success else "Failed to mark email as read"
        })
        
    except Exception as e:
        error_msg = f"An error occurred: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"success": False, "error": error_msg})

def mark_email_as_spam(message_id: str) -> str:
    """
    Mark an email as spam.
    
    Args:
        message_id (str): The ID of the message to mark as spam
        
    Returns:
        str: JSON string with the result
    """
    try:
        # Get credentials path and create service
        credentials_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'credentials', 'google_credentials.json')
        gmail_service = GmailService(credentials_path)
        
        # Get service
        service, error = gmail_service.get_service()
        if error:
            return json.dumps({"success": False, "error": error})
        
        # Mark as spam
        success, error = gmail_service.mark_as_spam(message_id)
        return json.dumps({
            "success": success,
            "error": error,
            "message": "Email marked as spam" if success else "Failed to mark email as spam"
        })
        
    except Exception as e:
        error_msg = f"An error occurred: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"success": False, "error": error_msg})

def get_email_labels() -> str:
    """
    Get all available email labels.
    
    Returns:
        str: JSON string containing the list of labels
    """
    try:
        # Get credentials path and create service
        credentials_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'credentials', 'google_credentials.json')
        gmail_service = GmailService(credentials_path)
        
        # Get service
        service, error = gmail_service.get_service()
        if error:
            return json.dumps({"success": False, "error": error})
        
        # Get labels
        labels, error = gmail_service.read_labels()
        if error:
            return json.dumps({"success": False, "error": error})
            
        # Return just the list of label names
        label_names = [label['name'] for label in labels]
        return json.dumps(label_names)
        
    except Exception as e:
        error_msg = f"An error occurred: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"success": False, "error": error_msg})

def create_email_label(label_name: str) -> str:
    """
    Create a new email label.
    
    Args:
        label_name (str): Name of the label to create
        
    Returns:
        str: JSON string with the created label info
    """
    try:
        # Get credentials path and create service
        credentials_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'credentials', 'google_credentials.json')
        gmail_service = GmailService(credentials_path)
        
        # Get service
        service, error = gmail_service.get_service()
        if error:
            return json.dumps({"success": False, "error": error})
        
        # Create label
        label, error = gmail_service.create_label(label_name)
        return json.dumps({
            "success": bool(label),
            "error": error,
            "label": label
        })
        
    except Exception as e:
        error_msg = f"An error occurred: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"success": False, "error": error_msg})

def extract_message_id(email_input: Union[str, Dict[str, Any]]) -> str:
    """
    Extract a proper Gmail message ID from an email string or object.
    
    Args:
        email_input: Either a string (potentially containing an email address) or an email object
        
    Returns:
        str: The clean message ID that can be used with Gmail API
    """
    if isinstance(email_input, dict):
        # If it's an email object, extract the ID field directly
        if 'id' in email_input:
            return email_input['id'].strip()
    
    # If it's a string, clean it
    if isinstance(email_input, str):
        # Remove angle brackets from potential email strings like <id@mail.gmail.com>
        clean_id = email_input.strip()
        if clean_id.startswith('<') and clean_id.endswith('>'):
            # This is likely an email address format, not a message ID
            # In this case, log a warning and return as is - validation will catch this later
            logger.warning(f"Received potential email address as message ID: {clean_id}")
            return clean_id
        
        return clean_id
    
    # Return as is if we can't determine the format
    return str(email_input)

def attach_label_to_email(message_id: str, label_id: str) -> str:
    """
    Attach a label to an email.
    
    Args:
        message_id (str): The ID of the message to label
        label_id (str): The ID or name of the label to attach
        
    Returns:
        str: JSON string with the result
    """
    try:
        # Clean and validate the message ID
        clean_message_id = extract_message_id(message_id)
        
        # Get credentials path and create service
        credentials_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'credentials', 'google_credentials.json')
        gmail_service = GmailService(credentials_path)
        
        # Get service
        service, error = gmail_service.get_service()
        if error:
            return json.dumps({"success": False, "error": error})
        
        # Check if label_id is actually a label name and convert it to ID if necessary
        actual_label_id = label_id
        if not label_id.startswith("LABEL_") and not label_id in ["INBOX", "SENT", "DRAFT", "TRASH", "SPAM", "UNREAD", "STARRED", "IMPORTANT"]:
            # This looks like a label name, not an ID - get the actual ID
            labels, error = gmail_service.read_labels()
            if error:
                return json.dumps({"success": False, "error": f"Error reading labels: {error}"})
            
            # Look for the label by name
            label_found = False
            for label in labels:
                if label['name'].lower() == label_id.lower():
                    actual_label_id = label['id']
                    label_found = True
                    logger.info(f"Converted label name '{label_id}' to ID '{actual_label_id}'")
                    break
            
            if not label_found:
                return json.dumps({
                    "success": False,
                    "error": f"Label '{label_id}' not found. Please create it first or check the name.",
                    "message": "Failed to attach label - label not found"
                })
        
        # Instead of recursively calling attach_label_to_email, use service directly
        try:
            service.users().messages().modify(
                userId='me',
                id=clean_message_id,
                body={'addLabelIds': [actual_label_id]}
            ).execute()
            success = True
            error = None
        except Exception as e:
            success = False
            error = str(e)
            logger.error(f"Error attaching label {actual_label_id} to message {clean_message_id}: {error}")
            
        if not success and error and ("Invalid id value" in error or "Invalid message_id" in error):
            # Provide more helpful error message
            return json.dumps({
                "success": False, 
                "error": f"Invalid Gmail message ID format: {message_id}. Please use the actual Gmail message ID, not the email address.",
                "message": "Failed to attach label due to invalid message ID format."
            })
        
        return json.dumps({
            "success": success,
            "error": error,
            "message": "Label attached successfully" if success else "Failed to attach label"
        })
        
    except Exception as e:
        error_msg = f"An error occurred: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"success": False, "error": error_msg})

if __name__ == "__main__":
    # Get unread emails as JSON
    json_result, error = get_unread_emails_json(max_results=5)
    if error:
        print(f"Error: {error}")
    else:
        print(json_result) 