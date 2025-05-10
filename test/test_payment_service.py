# test_payment_service.py
import pytest
from fastapi.testclient import TestClient
from payment_service.main import app
import os
import uuid
from unittest.mock import patch

client = TestClient(app)

# Mock the email sending and logging functions
@pytest.fixture(autouse=True)
def mock_external_services():
    with patch('payment_service.main.mailer.send_template_email', return_value=True), \
         patch('payment_service.main.logger.info'), \
         patch('payment_service.main.logger.warning'), \
         patch('payment_service.main.logger.error'), \
         patch('payment_service.main.logger.debug'):
        yield

def test_payment_service_list():
    """Test retrieving all available payment services"""
    response = client.get("/payments/services")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_payment():
    """Test retrieving a single payment service"""
    # First create a service
    service_data = {
        "service_id": "TEST001",
        "name": "Test Payment Service 1",
        "description": "This is the second test payment service",
        "base_price": 200.0
    }
    client.post("/payments/services", json=service_data)
    
    # Test retrieving
    response = client.get("/payments/services/TEST001")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Payment Service 1"

def test_add_new_payment_service():
    """Test adding a new payment service"""
    new_service = {
        "service_id": "classroom_premium",
        "name": "Premium Classroom Plan",
        "description": "Classroom with more equipment",
        "base_price": 200
    }
    response = client.post("/payments/services", json=new_service)
    assert response.status_code == 200
    assert response.json()["service_id"] == new_service["service_id"]

def test_update_payment_service():
    """Test updating a payment service"""
    # First create a service
    service_data = {
        "service_id": "TEST002",
        "name": "Test Payment Service 2",
        "description": "This is the third test payment service",
        "base_price": 300.0
    }
    client.post("/payments/services", json=service_data)
    
    # Update the service
    update_data = {
        "name": "Updated Service 2",
        "description": "This is the updated description",
        "base_price": 350.0
    }
    response = client.put("/payments/services/TEST002", json=update_data)
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Service 2"
    assert response.json()["base_price"] == 350.0

def test_delete_payment_service():
    """Test deleting a payment service"""
    # First create a service
    service_data = {
        "service_id": "TEST003",
        "name": "Test Payment Service 3",
        "description": "This is the third test payment service",
        "base_price": 400.0
    }
    client.post("/payments/services", json=service_data)
    
    # Delete the service
    response = client.delete("/payments/services/TEST003")
    assert response.status_code == 200
    
    # Confirm the service has been deleted
    response = client.get("/payments/services/TEST003")
    assert response.status_code == 404
    
def test_create_payment():
    """Test creating a new payment order"""
    # First create a service
    service_data = {
        "service_id": "classroom_standard",
        "name": "Standard Classroom Plan",
        "description": "Basic classroom booking service",
        "base_price": 100.0
    }
    client.post("/payments/services", json=service_data)

    # Then create a payment
    payment_data = {
        "service_id": "classroom_standard",
        "amount": 100,
        "user_id": "test_user",
        "email": "test_create_payment@example.com"
    }
    response = client.post("/payments/create", json=payment_data)
    assert response.status_code == 200
    assert "payment_id" in response.json()

def test_get_payment_info():
    """Test querying payment status"""
    # First create a service
    service_data = {
        "service_id": "test_service_info",
        "name": "Test Service Info",
        "description": "Service for payment info test",
        "base_price": 150.0
    }
    client.post("/payments/services", json=service_data)
    
    # Then create a payment order
    payment_data = {
        "service_id": "test_service_info",
        "amount": 150.0,
        "user_id": "test_user_456",
        "email": "test_payment_info@example.com"
    }
    create_response = client.post("/payments/create", json=payment_data)
    assert create_response.status_code == 200
    
    # Get the payment_id from the response
    payment_id = create_response.json()["payment_id"]
    
    # Now test querying the payment status
    response = client.get(f"/payments/{payment_id}/info")
    assert response.status_code == 200
    assert response.json()["amount"] == 150.0
    assert response.json()["status"] == "pending"
    
def test_update_payment_status():
    """Test updating payment order status"""
    # First create a service
    service_data = {
        "service_id": "test_service_update",
        "name": "Test Service Update",
        "description": "Service for payment update test",
        "base_price": 100.0
    }
    client.post("/payments/services", json=service_data)
    
    # Then create a payment order
    payment_data = {
        "service_id": "test_service_update",
        "amount": 100,
        "user_id": "test_user",
        "email": "test_update_status@example.com"
    }
    create_response = client.post("/payments/create", json=payment_data)
    assert create_response.status_code == 200
    payment_id = create_response.json()["payment_id"]
    
    # Update payment status
    update_data = {
        "status": "paid"
    }
    response = client.put(f"/payments/{payment_id}", json=update_data)
    assert response.status_code == 200
    assert response.json()["status"] == "paid"
    
    # Test updating a non-existent payment order
    update_data = {
        "status": "paid"
    }
    response = client.put("/payments/non_existent_id", json=update_data)
    assert response.status_code == 404

def test_delete_payment():
    """Test deleting a payment order"""
    # First create a service
    service_data = {
        "service_id": "test_service_delete",
        "name": "Test Service Delete",
        "description": "Service for payment deletion test",
        "base_price": 100.0
    }
    client.post("/payments/services", json=service_data)
    
    # Then create a payment order
    payment_data = {
    "service_id": "test_service_delete",
    "amount": 100,
    "user_id": "test_user",
    "email": "test_delete@example.com"
    }
    create_response = client.post("/payments/create", json=payment_data)
    assert create_response.status_code == 200
    payment_id = create_response.json()["payment_id"]
    
    # Delete the payment order
    response = client.delete(f"/payments/{payment_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "Payment deleted successfully"
    
    # Confirm the order has been deleted
    get_response = client.get(f"/payments/{payment_id}/info")
    assert get_response.status_code == 404

    # Test deleting a non-existent payment order
    response = client.delete("/payments/non_existent_id")
    assert response.status_code == 404

def create_test_application():
    """Helper function to create a test payment application and return its ID"""
    # Create a service
    service_data = {
        "service_id": "TEST008",
        "name": "Test Payment Service 8",
        "description": "Service for payment application test",
        "base_price": 450.0
    }
    client.post("/payments/services", json=service_data)
    
    # Apply for payment
    application_data = {
        "user_id": "user202",
        "service_id": "TEST008",
        "amount": 450.0,
        "reason": "Testing payment application",
        "email": "test_apply@example.com"
    }
    response = client.post("/payments/apply", json=application_data)
    assert response.status_code == 200
    assert "application_id" in response.json()
    assert response.json()["status"] == "pending"
    
    # Return application_id for other tests to use
    return response.json()["application_id"]

def test_apply_payment():
    """Test applying for payment"""
    create_test_application()

def test_get_application_info():
    """Test getting application info"""
    application_id = create_test_application()
    
    # Get application status
    response = client.get(f"/payments/applications/{application_id}")
    assert response.status_code == 200
    assert response.json()["application_id"] == application_id
    assert response.json()["status"] == "pending"

def test_approve_application():
    """Test approving payment application"""
    application_id = create_test_application()
    
    # Approve application
    response = client.put(f"/payments/applications/{application_id}/approve")
    assert response.status_code == 200
    assert "message" in response.json()
    assert "payment_id" in response.json()
    
    # Verify application status
    status_response = client.get(f"/payments/applications/{application_id}")
    assert status_response.json()["status"] == "approved"

def test_reject_application():
    """Test rejecting payment application"""
    application_id = create_test_application()
    
    # Reject application with reason parameter
    reason = "Insufficient information provided"
    response = client.put(f"/payments/applications/{application_id}/reject?reason={reason}")
    assert response.status_code == 200
    assert response.json()["message"] == "Application rejected"
    
    # Verify application status
    status_response = client.get(f"/payments/applications/{application_id}")
    assert status_response.json()["status"] == "rejected"

def test_download_payment():
    """Test downloading payment information"""
    # Create a service and payment
    service_data = {
        "service_id": "TEST009",
        "name": "Test Payment Service 9",
        "description": "Service for payment download test",
        "base_price": 500.0
    }
    client.post("/payments/services", json=service_data)
    
    payment_data = {
        "service_id": "TEST009",
        "amount": 500.0,
        "user_id": "user303",
        "email": "test_download@example.com"
    }
   
    create_response = client.post("/payments/create", json=payment_data)
    assert create_response.status_code == 200
    payment_id = create_response.json()["payment_id"]
    
    response = client.get(f"/payments/{payment_id}/download")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert f"payment_{payment_id}.csv" in response.headers["content-disposition"]
    
    content = response.content.decode("utf-8")
    assert "Payment ID" in content
    assert "TEST009" in content

def test_process_payment():
    """Test processing a payment"""
    # Create a service
    service_data = {
        "service_id": "test_process",
        "name": "Test Process Service",
        "description": "Service for payment processing test",
        "base_price": 200.0
    }
    client.post("/payments/services", json=service_data)
    
    # Create a payment
    payment_data = {
        "service_id": "test_process",
        "amount": 200.0,
        "user_id": "user_process",
        "email": "test_process@example.com"
    }
    create_response = client.post("/payments/create", json=payment_data)
    assert create_response.status_code == 200
    payment_id = create_response.json()["payment_id"]
    
    # Process the payment
    process_data = {
        "transaction_id": "trans_123456"
    }
    response = client.post(f"/payments/{payment_id}/process", json=process_data)
    assert response.status_code == 200
    assert response.json()["status"] == "paid"
    
    # Verify payment status
    status_response = client.get(f"/payments/{payment_id}/info")
    assert status_response.json()["status"] == "paid"

def test_fail_payment():
    """Test failing a payment"""
    # Create a service
    service_data = {
        "service_id": "test_fail",
        "name": "Test Fail Service",
        "description": "Service for payment failure test",
        "base_price": 150.0
    }
    client.post("/payments/services", json=service_data)
    
    # Create a payment
    payment_data = {
        "service_id": "test_fail",
        "amount": 150.0,
        "user_id": "user_fail",
        "email": "test_fail@example.com"
    }
    create_response = client.post("/payments/create", json=payment_data)
    assert create_response.status_code == 200
    payment_id = create_response.json()["payment_id"]
    
    # Fail the payment
    response = client.post(f"/payments/{payment_id}/fail")
    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    
    # Verify payment status
    status_response = client.get(f"/payments/{payment_id}/info")
    assert status_response.json()["status"] == "failed"

def test_export_payments():
    """Test exporting all payments"""
    # Create a few payments first with their services
    for i in range(3):
        # Create service
        service_data = {
            "service_id": f"test_export_{i}",
            "name": f"Test Export Service {i}",
            "description": f"Service for export test {i}",
            "base_price": 100.0 + i * 50
        }
        client.post("/payments/services", json=service_data)
        
        # Create payment
        payment_data = {
            "service_id": f"test_export_{i}",
            "amount": 100.0 + i * 50,
            "user_id": f"user_export_{i}",
            "email": f"test_export_{i}@example.com"
        }
        client.post("/payments/create", json=payment_data)
    
    # Export all payments
    response = client.get("/export/payments")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "all_payments_" in response.headers["content-disposition"]
    
    content = response.content.decode("utf-8")
    assert "Payment ID" in content
    assert "Service ID" in content
    assert "Email" in content
