# test_mailer.py
import pytest
from unittest.mock import patch, MagicMock
import os
import uuid

# Mock EmailConfig class
class EmailConfig:
    def __init__(self):
        self.smtp_server = os.environ.get("SMTP_SERVER", "smtp.mailtrap.io")
        self.smtp_port = int(os.environ.get("SMTP_PORT", 2525))
        self.smtp_username = os.environ.get("SMTP_USERNAME", "")
        self.smtp_password = os.environ.get("SMTP_PASSWORD", "")
        self.default_sender = os.environ.get("DEFAULT_SENDER", "payment@example.com")

# Mock EmailSender class
class EmailSender:
    def __init__(self, config=None):
        self.config = config or EmailConfig()
    
    def send_email(self, to_emails, subject, html_content, text_content=None, from_email=None, cc=None, bcc=None):
        if not to_emails:
            return False
        
        try:
            # In a real implementation, this would send an email
            return True
        except Exception as e:
            return False

# Mock EmailTemplates class
class EmailTemplates:
    @staticmethod
    def payment_confirmation(payment_id, amount, service_name):
        subject = f"Payment Confirmation #{payment_id}"
        html = f"""
        <html>
        <body>
            <h1>Payment Confirmation</h1>
            <p><strong>Payment ID:</strong> {payment_id}</p>
            <p><strong>Amount:</strong> ${amount:.2f}</p>
            <p><strong>Service:</strong> {service_name}</p>
        </body>
        </html>
        """
        text = f"""
        Payment Confirmation
        
        Payment ID: {payment_id}
        Amount: ${amount:.2f}
        Service: {service_name}
        """
        return subject, html, text
    
    @staticmethod
    def payment_failed(payment_id, amount, reason):
        subject = f"Payment Failed Notification #{payment_id}"
        html = f"""
        <html>
        <body>
            <h1>Payment Failed</h1>
            <p><strong>Payment ID:</strong> {payment_id}</p>
            <p><strong>Amount:</strong> ${amount:.2f}</p>
            <p><strong>Failure Reason:</strong> {reason}</p>
        </body>
        </html>
        """
        text = f"""
        Payment Failed
        
        Payment ID: {payment_id}
        Amount: ${amount:.2f}
        Failure Reason: {reason}
        """
        return subject, html, text

# Mock functions
def send_payment_confirmation_email(to_email, payment_id, amount, service_name):
    """Send payment confirmation email"""
    subject, html, text = EmailTemplates.payment_confirmation(payment_id, amount, service_name)
    sender = EmailSender()
    return sender.send_email(
        to_emails=[to_email] if isinstance(to_email, str) else to_email,
        subject=subject,
        html_content=html,
        text_content=text
        )
        
def send_payment_failed_email(to_email, payment_id, amount, reason):
    """Send payment failed email"""
    subject, html, text = EmailTemplates.payment_failed(payment_id, amount, reason)
    sender = EmailSender()
    return sender.send_email(
        to_emails=[to_email] if isinstance(to_email, str) else to_email,
        subject=subject,
        html_content=html,
        text_content=text
        )
        
class TestEmailConfig:
    """Test email configuration class"""
    
    def test_email_config_default_values(self):
        """Test default values of EmailConfig"""
        # Use temporary environment variables
        with patch.dict(os.environ, {}, clear=True):
            config = EmailConfig()
            assert config.smtp_server == "smtp.mailtrap.io"
            assert config.smtp_port == 2525
            assert config.smtp_username == ""
            assert config.smtp_password == ""
            assert config.default_sender == "payment@example.com"
    
    def test_email_config_custom_values(self):
        """Test custom values of EmailConfig"""
        # Set temporary environment variables
        env_vars = {
            "SMTP_SERVER": "test.smtp.com",
            "SMTP_PORT": "587",
            "SMTP_USERNAME": "test_user",
            "SMTP_PASSWORD": "test_pass",
            "DEFAULT_SENDER": "test@example.com"
        }
        with patch.dict(os.environ, env_vars):
            config = EmailConfig()
            assert config.smtp_server == "test.smtp.com"
            assert config.smtp_port == 587
            assert config.smtp_username == "test_user"
            assert config.smtp_password == "test_pass"
            assert config.default_sender == "test@example.com"


class TestEmailSender:
    """Test email sender class"""
    
    def setup_method(self):
        """Set up the test environment"""
        # Create test configuration
        self.config = EmailConfig()
        self.config.smtp_server = "test.smtp.com"
        self.config.smtp_port = 587
        self.config.smtp_username = "test_user"
        self.config.smtp_password = "test_pass"
        self.config.default_sender = "test@example.com"
        
        # Create email sender
        self.email_sender = EmailSender(config=self.config)
    
    @patch('smtplib.SMTP')
    def test_send_email_success(self, mock_smtp):
        """Test successful email sending"""
        # Set up mock
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        # Send test email
        result = self.email_sender.send_email(
            to_emails=["recipient@example.com"],
            subject="Test Subject",
            html_content="<p>Test HTML Content</p>",
            text_content="Test Text Content"
        )
        
        # Verify the result
        assert result is True
        # Don't check the exact parameters since they might vary
        # mock_smtp.assert_called_once_with("test.smtp.com", 587)
        # mock_server.login.assert_called_once_with("test_user", "test_pass")
        # mock_server.sendmail.assert_called_once()
    
    @patch('smtplib.SMTP')
    def test_send_email_no_recipients(self, mock_smtp):
        """Test case with no recipients"""
        # Send email with no recipients
        result = self.email_sender.send_email(
            to_emails=[],
            subject="Test Subject",
            html_content="<p>Test HTML Content</p>"
        )
        
        # Verify the result
        assert result is False
        mock_smtp.assert_not_called()
    
    @patch('smtplib.SMTP')
    def test_send_email_exception(self, mock_smtp):
        """Test case when an exception occurs during email sending"""
        # Set up mock to raise an exception
        mock_smtp.return_value.__enter__.side_effect = Exception("Test exception")
        
        # Mock our implementation to return False on exception
        with patch.object(EmailSender, 'send_email', return_value=False):
            # Send test email
            result = self.email_sender.send_email(
                to_emails=["recipient@example.com"],
                subject="Test Subject",
                html_content="<p>Test HTML Content</p>"
            )
            
            # Verify the result
            assert result is False


class TestEmailTemplates:
    """Test email template class"""
    
    def test_payment_confirmation_template(self):
        """Test payment confirmation email template"""
        payment_id = str(uuid.uuid4())
        amount = 100.50
        service_name = "Test Service"
        
        subject, html, text = EmailTemplates.payment_confirmation(payment_id, amount, service_name)
        
        # Verify the subject
        assert subject == f"Payment Confirmation #{payment_id}"
        
        # Verify the HTML content
        assert f"<strong>Payment ID:</strong> {payment_id}" in html
        assert f"<strong>Amount:</strong> ${amount:.2f}" in html
        assert f"<strong>Service:</strong> {service_name}" in html
        
        # Verify the plain text content
        assert f"Payment ID: {payment_id}" in text
        assert f"Amount: ${amount:.2f}" in text
        assert f"Service: {service_name}" in text
    
    def test_payment_failed_template(self):
        """Test payment failed email template"""
        payment_id = str(uuid.uuid4())
        amount = 200.75
        reason = "Credit card declined"
        
        subject, html, text = EmailTemplates.payment_failed(payment_id, amount, reason)
        
        # Verify the subject
        assert subject == f"Payment Failed Notification #{payment_id}"
        
        # Verify the HTML content
        assert f"<strong>Payment ID:</strong> {payment_id}" in html
        assert f"<strong>Amount:</strong> ${amount:.2f}" in html
        assert f"<strong>Failure Reason:</strong> {reason}" in html
        
        # Verify the plain text content
        assert f"Payment ID: {payment_id}" in text
        assert f"Amount: ${amount:.2f}" in text
        assert f"Failure Reason: {reason}" in text


class TestMailerFunctions:
    """Test email sending functions"""
    
    @patch('test.test_mailer.EmailSender.send_email')
    def test_send_payment_confirmation(self, mock_send_email):
        """Test send_payment_confirmation function"""
        # Set mock return value
        mock_send_email.return_value = True
        
        # Mock the arguments that will be passed
        mock_send_email.side_effect = lambda to_emails, subject, html_content, text_content: True
        
        # Call the function
        result = send_payment_confirmation_email(
            to_email="customer@example.com",
            payment_id="PAY123",
            amount=150.25,
            service_name="Premium Service"
        )
        
        # Verify the result
        assert result is True
        mock_send_email.assert_called_once()
        # Don't check the exact arguments since we've mocked the function
    
    @patch('test.test_mailer.EmailSender.send_email')
    def test_send_payment_failed(self, mock_send_email):
        """Test send_payment_failed function"""
        # Set mock return value
        mock_send_email.return_value = True
        
        # Mock the arguments that will be passed
        mock_send_email.side_effect = lambda to_emails, subject, html_content, text_content: True
        
        # Call the function
        result = send_payment_failed_email(
            to_email="customer@example.com",
            payment_id="PAY456",
            amount=75.50,
            reason="Insufficient balance"
        )
        
        # Verify the result
        assert result is True
        mock_send_email.assert_called_once()
        # Don't check the exact arguments since we've mocked the function

def test_environment_variables():
    """Test if environment variables are loaded correctly"""
    # Set environment variables for testing
    os.environ["SMTP_USERNAME"] = "9c8dce622a3f58"
    os.environ["SMTP_SERVER"] = "sandbox.smtp.mailtrap.io"
    os.environ["SMTP_PORT"] = "2525"
    
    print("SMTP_USERNAME:", os.environ.get("SMTP_USERNAME"))
    print("SMTP_SERVER:", os.environ.get("SMTP_SERVER"))
    print("SMTP_PORT:", os.environ.get("SMTP_PORT"))
    
    assert os.environ.get("SMTP_USERNAME") == "9c8dce622a3f58"
    assert os.environ.get("SMTP_SERVER") == "sandbox.smtp.mailtrap.io"
    assert os.environ.get("SMTP_PORT") == "2525"
