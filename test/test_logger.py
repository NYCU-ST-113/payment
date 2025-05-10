import pytest
from fastapi.testclient import TestClient
from logger_service.main import get_logger, log_to_file, log_info
from logger_service.main import app
from common_utils.logger.client import LoggerClient
import os
import uuid
import logging
import json
import time
from unittest.mock import patch, MagicMock

client = TestClient(app)

def test_logger_creation():
    """Test that logger is created correctly"""
    logger = get_logger("test_logger")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_logger"

def test_log_info(tmpdir):
    """Test that log_info writes to file"""
    # Temporarily modify the log directory for testing
    import logger_service.main
    original_log_dir = logger_service.main.LOG_DIR
    logger_service.main.LOG_DIR = str(tmpdir)
    
    # Reconfigure the log handler
    log_file = os.path.join(str(tmpdir), "test.log")
    handler = logging.FileHandler(log_file)
    formatter = logging.Formatter('%(message)s')  # Simplify the format for testing
    handler.setFormatter(formatter)
    
    logger = get_logger("test_logger")
    for h in logger.handlers[:]:
        logger.removeHandler(h)
    logger.addHandler(handler)
    
    # Write to the log
    test_message = "This is a test log message"
    log_info(test_message, "test_logger")
    
    # Check the log file
    handler.flush()
    with open(log_file, "r") as f:
        content = f.read()
    
    assert test_message in content
    
    # Restore the original path
    logger_service.main.LOG_DIR = original_log_dir

def test_log_endpoint():
    """Test the /log endpoint"""
    log_data = {
        "message": f"Test log message {uuid.uuid4()}",
        "level": "info",
        "service": "test_service"
    }
    
    response = client.post("/log", json=log_data)
    assert response.status_code == 200
    assert response.json() == {"status": "success"}

def test_log_batch_endpoint():
    """Test the /log/batch endpoint"""
    log_entries = [
        {
            "message": f"Test batch log 1 {uuid.uuid4()}",
            "level": "info",
            "service": "test_service"
        },
        {
            "message": f"Test batch log 2 {uuid.uuid4()}",
            "level": "error",
            "service": "test_service"
        }
    ]
    
    response = client.post("/log/batch", json={"logs": log_entries})
    assert response.status_code == 200
    assert response.json() == {"status": "success", "count": 2}

@patch('logger_service.main.log_to_file')
def test_log_endpoint_calls_log_info(mock_log_to_file):
    """Test that the /log endpoint calls log_to_file with correct parameters"""
    log_data = {
        "message": "Test message",
        "level": "info",
        "service": "test_service"
    }
    
    response = client.post("/log", json=log_data)
    assert response.status_code == 200
    
    # Check that log_to_file was called
    mock_log_to_file.assert_called_once()
    # Since log_to_file takes a LogEntry object, we check differently
    args, _ = mock_log_to_file.call_args
    log_entry = args[0]
    assert log_entry.message == log_data["message"]
    assert log_entry.service == log_data["service"]
    assert log_entry.level == log_data["level"]

def test_log_performance():
    """Test the performance of logging multiple messages"""
    log_entries = []
    for i in range(50):  # Test with 50 log entries
        log_entries.append({
            "message": f"Performance test log {i}",
            "level": "info",
            "service": "test_service"
        })
    
    start_time = time.time()
    response = client.post("/log/batch", json={"logs": log_entries})
    end_time = time.time()
    
    assert response.status_code == 200
    # Check that batch logging is reasonably fast (adjust threshold as needed)
    assert end_time - start_time < 1.0  # Should complete in less than 1 second

def test_logger_client():
    """Test the logger client functionality"""
    
    # Create a mock server response
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Initialize the logger client with correct parameters
        logger_client = LoggerClient(service_name="test_client_service", logger_url="http://test-logger-service")
        
        # Test info method
        result = logger_client.info("Test message")
        assert result is True  # LoggerClient methods return boolean values
        
        # Verify the request was made correctly with correct timeout
        mock_post.assert_called_with(
            "http://test-logger-service/log",
            json={
                "message": "Test message",
                "level": "INFO",  # Note: actual implementation uses uppercase log levels
                "service": "test_client_service",
                "timestamp": mock_post.call_args[1]['json']['timestamp']  # Dynamically get timestamp
            },
            timeout=2  # Actual implementation uses 2 second timeout
        )
        
        # Test error method
        mock_post.reset_mock()
        mock_response.status_code = 200
        
        result = logger_client.error("Test error message")
        assert result is True  # LoggerClient methods return boolean values
        
        # Verify the error request was made correctly
        mock_post.assert_called_with(
            "http://test-logger-service/log",
            json={
                "message": "Test error message",
                "level": "ERROR",  # Note: actual implementation uses uppercase log levels
                "service": "test_client_service",
                "timestamp": mock_post.call_args[1]['json']['timestamp']  # Dynamically get timestamp
            },
            timeout=2  # Actual implementation uses 2 second timeout
        )
        
        # Test with details
        mock_post.reset_mock()
        mock_response.status_code = 200
        
        details = {"key": "value", "error_code": 123}
        result = logger_client.warning("Test warning with details", details=details)
        assert result is True
        
        # Verify the warning request with details was made correctly
        mock_post.assert_called_with(
            "http://test-logger-service/log",
            json={
                "message": "Test warning with details",
                "level": "WARNING",
                "service": "test_client_service",
                "timestamp": mock_post.call_args[1]['json']['timestamp'],
                "details": details
            },
            timeout=2
        )
        
        # Test failure scenario
        mock_post.reset_mock()
        mock_response.status_code = 500  # Simulate server error
        
        result = logger_client.debug("Test debug message")
        assert result is False  # Should return False on failure