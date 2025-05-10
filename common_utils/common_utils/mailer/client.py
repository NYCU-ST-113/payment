# common_utils/mailer/client.py
import requests
import os
from typing import List, Dict, Any, Optional, Union
class MailerClient:
    """
    Client for interacting with the Email Service.
    Provides a simple interface for sending emails from other microservices.
    """
    def __init__(self, service_name: str, base_url: Optional[str] = None):
        """
        Initialize the Email Service client.
        Args:
            service_name: Name of the service using this client (for logging)
            base_url: Base URL of the email service. If not provided, uses EMAIL_SERVICE_URL env var
                     or defaults to http://localhost:8001
        """
        self.service_name = service_name
        self.base_url = base_url or os.environ.get("EMAIL_SERVICE_URL", "http://localhost:8001")
    def send_email(self, 
                  to_email: Union[str, List[str]], 
                  subject: str, 
                  body: str, 
                  html_body: Optional[str] = None,
                  cc: Optional[List[str]] = None,
                  bcc: Optional[List[str]] = None,
                  sender: Optional[str] = None,
                  attachments: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Send an email through the Email Service.
        Args:
            to_email: Recipient email address or list of addresses
            subject: Email subject
            body: Plain text email body
            html_body: HTML version of email body (optional)
            cc: List of CC recipients (optional)
            bcc: List of BCC recipients (optional)
            sender: Custom sender email (optional, uses default if not specified)
            attachments: List of attachment objects (optional)
        Returns:
            Dict containing the response from the email service
        Raises:
            Exception: If the email service returns an error
        """
        # Convert single email to list if needed
        if isinstance(to_email, str):
            to_email = [to_email]
        payload = {
            "to": to_email,
            "subject": subject,
            "body": body,
            "source_service": self.service_name
        }
        # Add optional parameters if provided
        if html_body:
            payload["html_body"] = html_body
        if cc:
            payload["cc"] = cc
        if bcc:
            payload["bcc"] = bcc
        if sender:
            payload["sender"] = sender
        if attachments:
            payload["attachments"] = attachments
        try:
            response = requests.post(f"{self.base_url}/send", json=payload)
            response.raise_for_status()  # Raise exception for HTTP errors
            return response.json()
        except requests.exceptions.RequestException as e:
            error_msg = f"Error sending email: {str(e)}"
            raise Exception(error_msg)
    def send_template_email(self,
                           to_email: Union[str, List[str]],
                           template_id: str,
                           template_data: Dict[str, Any],
                           subject: Optional[str] = None,
                           cc: Optional[List[str]] = None,
                           bcc: Optional[List[str]] = None,
                           sender: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a templated email through the Email Service.
        Args:
            to_email: Recipient email address or list of addresses
            template_id: ID of the template to use
            template_data: Data to populate the template with
            subject: Email subject (optional, may be defined in template)
            cc: List of CC recipients (optional)
            bcc: List of BCC recipients (optional)
            sender: Custom sender email (optional)
        Returns:
            Dict containing the response from the email service
        Raises:
            Exception: If the email service returns an error
        """
        # Convert single email to list if needed
        if isinstance(to_email, str):
            to_email = [to_email]
        payload = {
            "to": to_email,
            "template_id": template_id,
            "template_data": template_data,
            "source_service": self.service_name
        }
        # Add optional parameters if provided
        if subject:
            payload["subject"] = subject
        if cc:
            payload["cc"] = cc
        if bcc:
            payload["bcc"] = bcc
        if sender:
            payload["sender"] = sender
        try:
            response = requests.post(f"{self.base_url}/send-template", json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            error_msg = f"Error sending template email: {str(e)}"
            raise Exception(error_msg)
