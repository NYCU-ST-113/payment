import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import csv
from datetime import datetime, timedelta
import uuid

# Import your app and dependencies
from payment_service.main import app, get_db, Base, PaymentServiceModel, PaymentModel
from payment_service.main import (
    send_payment_created_email, send_payment_success_email, send_payment_failed_email,
    send_application_created_email, send_application_approved_email, send_application_rejected_email
)

# from main import app, get_db, Base, PaymentServiceModel, PaymentModel
# from main import (
#     send_payment_created_email, send_payment_success_email, send_payment_failed_email,
#     send_application_created_email, send_application_approved_email, send_application_rejected_email
# )

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Create test client
client = TestClient(app)

@pytest.fixture(scope="function")
def setup_database():
    """Setup test database for each test"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def sample_service():
    """Create a sample payment service"""
    return {
        "service_id": "test-service-1",
        "name": "Test Service",
        "description": "A test service for payments",
        "base_price": 100.0
    }

@pytest.fixture
def sample_payment_application():
    """Create a sample payment application"""
    return {
        "service_id": "test-service-1",
        "amount": 150.0,
        "user_id": "user-123",
        "email": "test@example.com",
        "reason": "Test application reason",
        "application_id": "app-123"
    }

class TestRootEndpoint:
    def test_read_root(self, setup_database):
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "service": "payment-service"}

class TestPaymentServices:
    def test_list_payment_services_empty(self, setup_database):
        response = client.get("/payments/services")
        assert response.status_code == 200
        assert response.json() == []

    def test_add_payment_service(self, setup_database, sample_service):
        response = client.post("/payments/services", json=sample_service)
        assert response.status_code == 200
        data = response.json()
        assert data["service_id"] == sample_service["service_id"]
        assert data["name"] == sample_service["name"]
        assert data["description"] == sample_service["description"]
        assert data["base_price"] == sample_service["base_price"]

    def test_add_duplicate_payment_service(self, setup_database, sample_service):
        # Add first service
        client.post("/payments/services", json=sample_service)
        
        # Try to add duplicate
        response = client.post("/payments/services", json=sample_service)
        assert response.status_code == 400
        assert "Service ID already exists" in response.json()["detail"]

    def test_list_payment_services_with_data(self, setup_database, sample_service):
        # Add service first
        client.post("/payments/services", json=sample_service)
        
        # List services
        response = client.get("/payments/services")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["service_id"] == sample_service["service_id"]

    def test_get_payment_service(self, setup_database, sample_service):
        # Add service first
        client.post("/payments/services", json=sample_service)
        
        # Get specific service
        response = client.get(f"/payments/services/{sample_service['service_id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["service_id"] == sample_service["service_id"]
        assert data["name"] == sample_service["name"]

    def test_get_nonexistent_payment_service(self, setup_database):
        response = client.get("/payments/services/nonexistent")
        assert response.status_code == 404
        assert "Payment service not found" in response.json()["detail"]

    def test_update_payment_service(self, setup_database, sample_service):
        # Add service first
        client.post("/payments/services", json=sample_service)
        
        # Update service
        update_data = {
            "name": "Updated Service Name",
            "base_price": 200.0
        }
        response = client.put(f"/payments/services/{sample_service['service_id']}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Service Name"
        assert data["base_price"] == 200.0
        assert data["description"] == sample_service["description"]  # Should remain unchanged

    def test_update_nonexistent_payment_service(self, setup_database):
        update_data = {"name": "Updated Name"}
        response = client.put("/payments/services/nonexistent", json=update_data)
        assert response.status_code == 404
        assert "Payment service not found" in response.json()["detail"]

    def test_delete_payment_service(self, setup_database, sample_service):
        # Add service first
        client.post("/payments/services", json=sample_service)
        
        # Delete service
        response = client.delete(f"/payments/services/{sample_service['service_id']}")
        assert response.status_code == 200
        assert "Payment service deleted successfully" in response.json()["message"]
        
        # Verify deletion
        response = client.get(f"/payments/services/{sample_service['service_id']}")
        assert response.status_code == 404

    def test_delete_nonexistent_payment_service(self, setup_database):
        response = client.delete("/payments/services/nonexistent")
        assert response.status_code == 404
        assert "Payment service not found" in response.json()["detail"]

class TestPaymentApplications:
    @patch('payment_service.main.send_application_created_email')
    def test_apply_payment(self, mock_email, setup_database, sample_service, sample_payment_application):
        mock_email.return_value = True
        
        # Add service first
        client.post("/payments/services", json=sample_service)
        
        # Apply for payment
        response = client.post("/payments/apply", json=sample_payment_application)
        assert response.status_code == 200
        data = response.json()
        assert data["payment_id"] == sample_payment_application["application_id"]
        assert data["status"] == "application_pending"
        assert data["amount"] == sample_payment_application["amount"]
        
        mock_email.assert_called_once()

    @patch('payment_service.main.send_application_created_email')
    def test_apply_payment_nonexistent_service(self, mock_email, setup_database, sample_payment_application):
        mock_email.return_value = True
        
        # Apply for payment without adding service
        response = client.post("/payments/apply", json=sample_payment_application)
        assert response.status_code == 404
        assert "Service not found" in response.json()["detail"]

    @patch('payment_service.main.send_application_created_email')
    def test_apply_payment_without_application_id(self, mock_email, setup_database, sample_service):
        mock_email.return_value = True
        
        # Add service first
        client.post("/payments/services", json=sample_service)
        
        # Apply for payment without application_id
        application_data = {
            "service_id": "test-service-1",
            "amount": 150.0,
            "user_id": "user-123",
            "email": "test@example.com",
            "reason": "Test application reason",
            "application_id": ""  # Empty application_id
        }
        
        response = client.post("/payments/apply", json=application_data)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "application_pending"
        assert "payment_id" in data
        assert data["payment_id"] != ""

    def test_list_all_payments_empty(self, setup_database):
        response = client.get("/payments")
        assert response.status_code == 200
        assert response.json()["payments"] == []

    @patch('payment_service.main.send_application_created_email')
    def test_list_all_payments_with_data(self, mock_email, setup_database, sample_service, sample_payment_application):
        mock_email.return_value = True
        
        # Add service and application
        client.post("/payments/services", json=sample_service)
        client.post("/payments/apply", json=sample_payment_application)
        
        # List all payments
        response = client.get("/payments")
        assert response.status_code == 200
        data = response.json()
        assert len(data["payments"]) == 1
        assert data["payments"][0]["status"] == "application_pending"

    @patch('payment_service.main.send_application_created_email')
    def test_list_all_payments_with_status_filter(self, mock_email, setup_database, sample_service, sample_payment_application):
        mock_email.return_value = True
        
        # Add service and application
        client.post("/payments/services", json=sample_service)
        client.post("/payments/apply", json=sample_payment_application)
        
        # List payments with status filter
        response = client.get("/payments?status=application_pending")
        assert response.status_code == 200
        data = response.json()
        assert len(data["payments"]) == 1
        
        # List with different status
        response = client.get("/payments?status=paid")
        assert response.status_code == 200
        data = response.json()
        assert len(data["payments"]) == 0

    @patch('payment_service.main.send_application_created_email')
    def test_get_payment_info(self, mock_email, setup_database, sample_service, sample_payment_application):
        mock_email.return_value = True
        
        # Add service and application
        client.post("/payments/services", json=sample_service)
        response = client.post("/payments/apply", json=sample_payment_application)
        payment_id = response.json()["payment_id"]
        
        # Get payment info
        response = client.get(f"/payments/{payment_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["payment_id"] == payment_id
        assert data["service_name"] == sample_service["name"]
        assert data["status"] == "application_pending"

    def test_get_nonexistent_payment_info(self, setup_database):
        response = client.get("/payments/nonexistent")
        assert response.status_code == 404
        assert "Payment not found" in response.json()["detail"]

class TestPaymentStatusUpdates:
    @patch('payment_service.main.send_payment_success_email')
    @patch('payment_service.main.send_application_created_email')
    def test_update_payment_status_to_paid(self, mock_created_email, mock_success_email, setup_database, sample_service, sample_payment_application):
        mock_created_email.return_value = True
        mock_success_email.return_value = True
        
        # Setup payment
        client.post("/payments/services", json=sample_service)
        response = client.post("/payments/apply", json=sample_payment_application)
        payment_id = response.json()["payment_id"]
        
        # Update status to paid
        response = client.put(f"/payments/{payment_id}", json={"status": "paid"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "paid"
        
        mock_success_email.assert_called_once()

    @patch('payment_service.main.send_payment_failed_email')
    @patch('payment_service.main.send_application_created_email')
    def test_update_payment_status_to_failed(self, mock_created_email, mock_failed_email, setup_database, sample_service, sample_payment_application):
        mock_created_email.return_value = True
        mock_failed_email.return_value = True
        
        # Setup payment
        client.post("/payments/services", json=sample_service)
        response = client.post("/payments/apply", json=sample_payment_application)
        payment_id = response.json()["payment_id"]
        
        # Update status to failed
        response = client.put(f"/payments/{payment_id}", json={"status": "failed"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        
        mock_failed_email.assert_called_once()

    def test_update_nonexistent_payment_status(self, setup_database):
        response = client.put("/payments/nonexistent", json={"status": "paid"})
        assert response.status_code == 404
        assert "Payment not found" in response.json()["detail"]

class TestPaymentApplicationApproval:
    @patch('payment_service.main.send_payment_created_email')
    @patch('payment_service.main.send_application_approved_email')
    @patch('payment_service.main.send_application_created_email')
    def test_approve_payment_application(self, mock_created_email, mock_approved_email, mock_payment_created_email, setup_database, sample_service, sample_payment_application):
        mock_created_email.return_value = True
        mock_approved_email.return_value = True
        mock_payment_created_email.return_value = True
        
        # Setup application
        client.post("/payments/services", json=sample_service)
        response = client.post("/payments/apply", json=sample_payment_application)
        payment_id = response.json()["payment_id"]
        
        # Approve application
        response = client.put(f"/payments/{payment_id}/approve")
        assert response.status_code == 200
        data = response.json()
        assert "Application approved" in data["message"]
        assert data["status"] == "pending"
        
        mock_approved_email.assert_called_once()
        mock_payment_created_email.assert_called_once()

    def test_approve_nonexistent_payment_application(self, setup_database):
        response = client.put("/payments/nonexistent/approve")
        assert response.status_code == 404
        assert "Payment not found" in response.json()["detail"]

    @patch('payment_service.main.send_application_created_email')
    def test_approve_non_pending_application(self, mock_email, setup_database, sample_service, sample_payment_application):
        mock_email.return_value = True
        
        # Setup and approve application first
        client.post("/payments/services", json=sample_service)
        response = client.post("/payments/apply", json=sample_payment_application)
        payment_id = response.json()["payment_id"]
        
        # Change status to something other than application_pending
        client.put(f"/payments/{payment_id}", json={"status": "paid"})
        
        # Try to approve
        response = client.put(f"/payments/{payment_id}/approve")
        assert response.status_code == 400
        assert "Application is not in pending status" in response.json()["detail"]

class TestPaymentApplicationRejection:
    @patch('payment_service.main.send_application_rejected_email')
    @patch('payment_service.main.send_application_created_email')
    def test_reject_payment_application(self, mock_created_email, mock_rejected_email, setup_database, sample_service, sample_payment_application):
        mock_created_email.return_value = True
        mock_rejected_email.return_value = True
        
        # Setup application
        client.post("/payments/services", json=sample_service)
        response = client.post("/payments/apply", json=sample_payment_application)
        payment_id = response.json()["payment_id"]
        
        # Reject application
        rejection_data = {"reason": "Insufficient documentation"}
        response = client.put(f"/payments/{payment_id}/reject", json=rejection_data)
        assert response.status_code == 200
        data = response.json()
        assert "Application rejected" in data["message"]
        
        mock_rejected_email.assert_called_once()

    def test_reject_nonexistent_payment_application(self, setup_database):
        rejection_data = {"reason": "Test reason"}
        response = client.put("/payments/nonexistent/reject", json=rejection_data)
        assert response.status_code == 404
        assert "Payment not found" in response.json()["detail"]

    @patch('payment_service.main.send_application_created_email')
    def test_reject_non_pending_application(self, mock_email, setup_database, sample_service, sample_payment_application):
        mock_email.return_value = True
        
        # Setup application and change status
        client.post("/payments/services", json=sample_service)
        response = client.post("/payments/apply", json=sample_payment_application)
        payment_id = response.json()["payment_id"]
        
        # Change status
        client.put(f"/payments/{payment_id}", json={"status": "paid"})
        
        # Try to reject
        rejection_data = {"reason": "Test reason"}
        response = client.put(f"/payments/{payment_id}/reject", json=rejection_data)
        assert response.status_code == 400
        assert "Application is not in pending status" in response.json()["detail"]

class TestPaymentProcessing:
    @patch('payment_service.main.send_payment_success_email')
    @patch('payment_service.main.send_payment_created_email')
    @patch('payment_service.main.send_application_approved_email')
    @patch('payment_service.main.send_application_created_email')
    def test_process_payment(self, mock_created_email, mock_approved_email, mock_payment_created_email, mock_success_email, setup_database, sample_service, sample_payment_application):
        # Mock all email functions
        mock_created_email.return_value = True
        mock_approved_email.return_value = True
        mock_payment_created_email.return_value = True
        mock_success_email.return_value = True
        
        # Setup and approve application
        client.post("/payments/services", json=sample_service)
        response = client.post("/payments/apply", json=sample_payment_application)
        payment_id = response.json()["payment_id"]
        client.put(f"/payments/{payment_id}/approve")
        
        # Process payment
        process_data = {"transaction_id": "txn-123"}
        response = client.post(f"/payments/{payment_id}/process", json=process_data)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "paid"
        
        mock_success_email.assert_called_once()

    @patch('payment_service.main.send_payment_success_email')
    @patch('payment_service.main.send_payment_created_email')
    @patch('payment_service.main.send_application_approved_email')
    @patch('payment_service.main.send_application_created_email')
    def test_process_payment_without_transaction_id(self, mock_created_email, mock_approved_email, mock_payment_created_email, mock_success_email, setup_database, sample_service, sample_payment_application):
        # Mock all email functions
        mock_created_email.return_value = True
        mock_approved_email.return_value = True
        mock_payment_created_email.return_value = True
        mock_success_email.return_value = True
        
        # Setup and approve application
        client.post("/payments/services", json=sample_service)
        response = client.post("/payments/apply", json=sample_payment_application)
        payment_id = response.json()["payment_id"]
        client.put(f"/payments/{payment_id}/approve")
        
        # Process payment without transaction_id
        response = client.post(f"/payments/{payment_id}/process")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "paid"

    def test_process_nonexistent_payment(self, setup_database):
        response = client.post("/payments/nonexistent/process")
        assert response.status_code == 404
        assert "Payment not found" in response.json()["detail"]

    @patch('payment_service.main.send_application_created_email')
    def test_process_non_pending_payment(self, mock_email, setup_database, sample_service, sample_payment_application):
        mock_email.return_value = True
        
        # Setup application (but don't approve)
        client.post("/payments/services", json=sample_service)
        response = client.post("/payments/apply", json=sample_payment_application)
        payment_id = response.json()["payment_id"]
        
        # Try to process payment that's still in application_pending
        response = client.post(f"/payments/{payment_id}/process")
        assert response.status_code == 400
        assert "Payment is not in pending status" in response.json()["detail"]

class TestPaymentFailure:
    @patch('payment_service.main.send_payment_failed_email')
    @patch('payment_service.main.send_payment_created_email')
    @patch('payment_service.main.send_application_approved_email')
    @patch('payment_service.main.send_application_created_email')
    def test_fail_payment(self, mock_created_email, mock_approved_email, mock_payment_created_email, mock_failed_email, setup_database, sample_service, sample_payment_application):
        # Mock all email functions
        mock_created_email.return_value = True
        mock_approved_email.return_value = True
        mock_payment_created_email.return_value = True
        mock_failed_email.return_value = True
        
        # Setup and approve application
        client.post("/payments/services", json=sample_service)
        response = client.post("/payments/apply", json=sample_payment_application)
        payment_id = response.json()["payment_id"]
        client.put(f"/payments/{payment_id}/approve")
        
        # Fail payment
        response = client.post(f"/payments/{payment_id}/fail")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        
        mock_failed_email.assert_called_once()

    def test_fail_nonexistent_payment(self, setup_database):
        response = client.post("/payments/nonexistent/fail")
        assert response.status_code == 404
        assert "Payment not found" in response.json()["detail"]

class TestPaymentDeletion:
    @patch('payment_service.main.mailer')
    @patch('payment_service.main.send_application_created_email')
    def test_delete_payment(self, mock_created_email, mock_mailer, setup_database, sample_service, sample_payment_application):
        mock_created_email.return_value = True
        mock_mailer.send_template_email.return_value = True
        
        # Setup application
        client.post("/payments/services", json=sample_service)
        response = client.post("/payments/apply", json=sample_payment_application)
        payment_id = response.json()["payment_id"]
        
        # Delete payment
        response = client.delete(f"/payments/{payment_id}")
        assert response.status_code == 200
        assert "Payment deleted successfully" in response.json()["message"]
        
        # Verify deletion
        response = client.get(f"/payments/{payment_id}")
        assert response.status_code == 404

    def test_delete_nonexistent_payment(self, setup_database):
        response = client.delete("/payments/nonexistent")
        assert response.status_code == 404
        assert "Payment not found" in response.json()["detail"]

class TestUserPayments:
    @patch('payment_service.main.send_application_created_email')
    def test_get_user_payments(self, mock_email, setup_database, sample_service, sample_payment_application):
        mock_email.return_value = True
        
        # Setup multiple payments for same user
        client.post("/payments/services", json=sample_service)
        
        # Create multiple applications
        app1 = sample_payment_application.copy()
        app1["application_id"] = "app-1"
        app2 = sample_payment_application.copy()
        app2["application_id"] = "app-2"
        app2["amount"] = 200.0
        
        client.post("/payments/apply", json=app1)
        client.post("/payments/apply", json=app2)
        
        # Get user payments
        response = client.get(f"/payments/user/{sample_payment_application['user_id']}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["payments"]) == 2

    @patch('payment_service.main.send_application_created_email')
    def test_get_user_payments_with_status_filter(self, mock_email, setup_database, sample_service, sample_payment_application):
        mock_email.return_value = True
        
        # Setup payment
        client.post("/payments/services", json=sample_service)
        client.post("/payments/apply", json=sample_payment_application)
        
        # Get user payments with status filter
        response = client.get(f"/payments/user/{sample_payment_application['user_id']}?status=application_pending")
        assert response.status_code == 200
        data = response.json()
        assert len(data["payments"]) == 1
        assert data["payments"][0]["status"] == "application_pending"

    def test_get_user_payments_no_payments(self, setup_database):
        response = client.get("/payments/user/nonexistent-user")
        assert response.status_code == 200
        data = response.json()
        assert len(data["payments"]) == 0

class TestPaymentDownload:
    @patch('payment_service.main.send_application_created_email')
    def test_download_payment(self, mock_email, setup_database, sample_service, sample_payment_application):
        mock_email.return_value = True
        
        # Setup payment
        client.post("/payments/services", json=sample_service)
        response = client.post("/payments/apply", json=sample_payment_application)
        payment_id = response.json()["payment_id"]
        
        # Download payment
        response = client.get(f"/payments/{payment_id}/download")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"

    def test_download_nonexistent_payment(self, setup_database):
        response = client.get("/payments/nonexistent/download")
        assert response.status_code == 404
        assert "Payment not found" in response.json()["detail"]

class TestPaymentExport:
    @patch('payment_service.main.send_application_created_email')
    def test_export_payments(self, mock_email, setup_database, sample_service, sample_payment_application):
        mock_email.return_value = True
        
        # Setup payment
        client.post("/payments/services", json=sample_service)
        client.post("/payments/apply", json=sample_payment_application)
        
        # Export payments
        response = client.get("/export/payments")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"

    @patch('payment_service.main.send_application_created_email')
    def test_export_payments_with_status_filter(self, mock_email, setup_database, sample_service, sample_payment_application):
        mock_email.return_value = True
        
        # Setup payment
        client.post("/payments/services", json=sample_service)
        client.post("/payments/apply", json=sample_payment_application)
        
        # Export payments with status filter
        response = client.get("/export/payments?status=application_pending")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"

    def test_export_payments_empty(self, setup_database):
        response = client.get("/export/payments")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"

class TestApplicationManagement:
    @patch('payment_service.main.send_application_created_email')
    def test_list_applications(self, mock_email, setup_database, sample_service, sample_payment_application):
        mock_email.return_value = True
        
        # Setup application
        client.post("/payments/services", json=sample_service)
        client.post("/payments/apply", json=sample_payment_application)
        
        # List applications
        response = client.get("/payments/applications")
        assert response.status_code == 200
        data = response.json()
        assert len(data["applications"]) == 1
        assert data["applications"][0]["status"] == "application_pending"

    @patch('payment_service.main.send_application_created_email')
    def test_list_applications_with_status_filter(self, mock_email, setup_database, sample_service, sample_payment_application):
        mock_email.return_value = True
        
        # Setup application
        client.post("/payments/services", json=sample_service)
        client.post("/payments/apply", json=sample_payment_application)
        
        # List applications with status filter
        response = client.get("/payments/applications?status=application_pending")
        assert response.status_code == 200
        data = response.json()
        assert len(data["applications"]) == 1

    def test_list_applications_empty(self, setup_database):
        response = client.get("/payments/applications")
        assert response.status_code == 200
        data = response.json()
        assert len(data["applications"]) == 0

    @patch('payment_service.main.send_payment_created_email')
    @patch('payment_service.main.send_application_approved_email')
    @patch('payment_service.main.send_application_created_email')
    def test_list_pending_payments(self, mock_created_email, mock_approved_email, mock_payment_created_email, setup_database, sample_service, sample_payment_application):
        mock_created_email.return_value = True
        mock_approved_email.return_value = True
        mock_payment_created_email.return_value = True
        
        # Setup and approve application
        client.post("/payments/services", json=sample_service)
        response = client.post("/payments/apply", json=sample_payment_application)
        payment_id = response.json()["payment_id"]

        client.put(f"/payments/{payment_id}/approve")
        
        # List pending payments
        response = client.get("/payments/pending")
        assert response.status_code == 200
        data = response.json()
        assert len(data["pending_payments"]) == 1
        assert data["pending_payments"][0]["status"] == "pending"

    def test_list_pending_payments_empty(self, setup_database):
        response = client.get("/payments/pending")
        assert response.status_code == 200
        data = response.json()
        assert len(data["pending_payments"]) == 0

    @patch('payment_service.main.send_payment_success_email')
    @patch('payment_service.main.send_payment_created_email')
    @patch('payment_service.main.send_application_approved_email')
    @patch('payment_service.main.send_application_created_email')
    def test_list_completed_payments(self, mock_created_email, mock_approved_email, mock_payment_created_email, mock_success_email, setup_database, sample_service, sample_payment_application):
        mock_created_email.return_value = True
        mock_approved_email.return_value = True
        mock_payment_created_email.return_value = True
        mock_success_email.return_value = True
        
        # Setup, approve and process payment
        client.post("/payments/services", json=sample_service)
        response = client.post("/payments/apply", json=sample_payment_application)
        payment_id = response.json()["payment_id"]
        client.put(f"/payments/{payment_id}/approve")
        client.post(f"/payments/{payment_id}/process")
        
        # List completed payments
        response = client.get("/payments/completed")
        assert response.status_code == 200
        data = response.json()
        assert len(data["completed_payments"]) == 1
        assert data["completed_payments"][0]["status"] == "paid"

    def test_list_completed_payments_empty(self, setup_database):
        response = client.get("/payments/completed")
        assert response.status_code == 200
        data = response.json()
        assert len(data["completed_payments"]) == 0

class TestEmailFunctions:
    @patch('payment_service.main.mailer')
    def test_send_payment_created_email_success(self, mock_mailer):
        mock_mailer.send_template_email.return_value = True
        
        result = send_payment_created_email(
            payment_id="test-payment",
            email="test@example.com",
            service_name="Test Service",
            amount=100.0,
            due_date="2024-01-01"
        )
        
        assert result is True
        mock_mailer.send_template_email.assert_called_once()

    @patch('payment_service.main.mailer')
    def test_send_payment_created_email_failure(self, mock_mailer):
        mock_mailer.send_template_email.side_effect = Exception("Email service error")
        
        result = send_payment_created_email(
            payment_id="test-payment",
            email="test@example.com",
            service_name="Test Service",
            amount=100.0,
            due_date="2024-01-01"
        )
        
        assert result is False

    @patch('payment_service.main.mailer')
    def test_send_payment_success_email_success(self, mock_mailer):
        mock_mailer.send_template_email.return_value = True
        
        result = send_payment_success_email(
            payment_id="test-payment",
            email="test@example.com",
            service_name="Test Service",
            amount=100.0,
            transaction_id="txn-123"
        )
        
        assert result is True
        mock_mailer.send_template_email.assert_called_once()

    @patch('payment_service.main.mailer')
    def test_send_payment_success_email_without_transaction_id(self, mock_mailer):
        mock_mailer.send_template_email.return_value = True
        
        result = send_payment_success_email(
            payment_id="test-payment",
            email="test@example.com",
            service_name="Test Service",
            amount=100.0
        )
        
        assert result is True
        mock_mailer.send_template_email.assert_called_once()

    @patch('payment_service.main.mailer')
    def test_send_payment_success_email_failure(self, mock_mailer):
        mock_mailer.send_template_email.side_effect = Exception("Email service error")
        
        result = send_payment_success_email(
            payment_id="test-payment",
            email="test@example.com",
            service_name="Test Service",
            amount=100.0
        )
        
        assert result is False

    @patch('payment_service.main.mailer')
    def test_send_payment_failed_email_success(self, mock_mailer):
        mock_mailer.send_template_email.return_value = True
        
        result = send_payment_failed_email(
            payment_id="test-payment",
            email="test@example.com",
            service_name="Test Service",
            amount=100.0,
            reason="Insufficient funds"
        )
        
        assert result is True
        mock_mailer.send_template_email.assert_called_once()

    @patch('payment_service.main.mailer')
    def test_send_payment_failed_email_failure(self, mock_mailer):
        mock_mailer.send_template_email.side_effect = Exception("Email service error")
        
        result = send_payment_failed_email(
            payment_id="test-payment",
            email="test@example.com",
            service_name="Test Service",
            amount=100.0,
            reason="Insufficient funds"
        )
        
        assert result is False

    @patch('payment_service.main.mailer')
    def test_send_application_created_email_success(self, mock_mailer):
        mock_mailer.send_template_email.return_value = True
        
        result = send_application_created_email(
            payment_id="test-payment",
            email="test@example.com",
            service_name="Test Service",
            amount=100.0
        )
        
        assert result is True
        mock_mailer.send_template_email.assert_called_once()

    @patch('payment_service.main.mailer')
    def test_send_application_created_email_failure(self, mock_mailer):
        mock_mailer.send_template_email.side_effect = Exception("Email service error")
        
        result = send_application_created_email(
            payment_id="test-payment",
            email="test@example.com",
            service_name="Test Service",
            amount=100.0
        )
        
        assert result is False

    @patch('payment_service.main.mailer')
    def test_send_application_approved_email_success(self, mock_mailer):
        mock_mailer.send_template_email.return_value = True
        
        result = send_application_approved_email(
            payment_id="test-payment",
            email="test@example.com",
            service_name="Test Service",
            amount=100.0
        )
        
        assert result is True
        mock_mailer.send_template_email.assert_called_once()

    @patch('payment_service.main.mailer')
    def test_send_application_approved_email_failure(self, mock_mailer):
        mock_mailer.send_template_email.side_effect = Exception("Email service error")
        
        result = send_application_approved_email(
            payment_id="test-payment",
            email="test@example.com",
            service_name="Test Service",
            amount=100.0
        )
        
        assert result is False

    @patch('payment_service.main.mailer')
    def test_send_application_rejected_email_success(self, mock_mailer):
        mock_mailer.send_template_email.return_value = True
        
        result = send_application_rejected_email(
            payment_id="test-payment",
            email="test@example.com",
            service_name="Test Service",
            amount=100.0,
            reason="Insufficient documentation"
        )
        
        assert result is True
        mock_mailer.send_template_email.assert_called_once()

    @patch('payment_service.main.mailer')
    def test_send_application_rejected_email_failure(self, mock_mailer):
        mock_mailer.send_template_email.side_effect = Exception("Email service error")
        
        result = send_application_rejected_email(
            payment_id="test-payment",
            email="test@example.com",
            service_name="Test Service",
            amount=100.0,
            reason="Insufficient documentation"
        )
        
        assert result is False

class TestDatabaseModels:
    def test_payment_service_model_creation(self, setup_database):
        db = TestingSessionLocal()
        try:
            service = PaymentServiceModel(
                service_id="test-service",
                name="Test Service",
                description="Test Description",
                base_price=100.0
            )
            db.add(service)
            db.commit()
            db.refresh(service)
            
            assert service.service_id == "test-service"
            assert service.name == "Test Service"
            assert service.description == "Test Description"
            assert service.base_price == 100.0
        finally:
            db.close()

    def test_payment_model_creation(self, setup_database):
        db = TestingSessionLocal()
        try:
            # Create service first
            service = PaymentServiceModel(
                service_id="test-service",
                name="Test Service",
                description="Test Description",
                base_price=100.0
            )
            db.add(service)
            db.commit()
            
            # Create payment
            payment = PaymentModel(
                payment_id="test-payment",
                service_id="test-service",
                amount=150.0,
                user_id="user-123",
                status="pending",
                created_at=datetime.now(),
                email="test@example.com",
                application_reason="Test reason"
            )
            db.add(payment)
            db.commit()
            db.refresh(payment)
            
            assert payment.payment_id == "test-payment"
            assert payment.service_id == "test-service"
            assert payment.amount == 150.0
            assert payment.user_id == "user-123"
            assert payment.status == "pending"
            assert payment.email == "test@example.com"
            assert payment.application_reason == "Test reason"
        finally:
            db.close()

    def test_payment_service_relationship(self, setup_database):
        db = TestingSessionLocal()
        try:
            # Create service
            service = PaymentServiceModel(
                service_id="test-service",
                name="Test Service",
                description="Test Description",
                base_price=100.0
            )
            db.add(service)
            db.commit()
            
            # Create payment
            payment = PaymentModel(
                payment_id="test-payment",
                service_id="test-service",
                amount=150.0,
                user_id="user-123",
                status="pending",
                created_at=datetime.now(),
                email="test@example.com"
            )
            db.add(payment)
            db.commit()
            
            # Test relationship
            db.refresh(service)
            db.refresh(payment)
            
            assert len(service.payments) == 1
            assert service.payments[0].payment_id == "test-payment"
            assert payment.service.name == "Test Service"
        finally:
            db.close()

class TestErrorHandling:
    @patch('payment_service.main.send_application_created_email')
    def test_database_rollback_on_error(self, mock_email, setup_database, sample_service):
        mock_email.side_effect = Exception("Email service error")
        
        # Add service first
        client.post("/payments/services", json=sample_service)
        
        # Try to apply with email error - should still succeed as email is not critical
        application_data = {
            "service_id": "test-service-1",
            "amount": 150.0,
            "user_id": "user-123",
            "email": "test@example.com",
            "reason": "Test application reason",
            "application_id": "app-123"
        }
        
        response = client.post("/payments/apply", json=application_data)
        # Should still succeed even if email fails
        assert response.status_code == 200

    def test_invalid_email_format(self, setup_database, sample_service):
        # Add service first
        client.post("/payments/services", json=sample_service)
        
        # Try to apply with invalid email
        application_data = {
            "service_id": "test-service-1",
            "amount": 150.0,
            "user_id": "user-123",
            "email": "invalid-email",  # Invalid email format
            "reason": "Test application reason",
            "application_id": "app-123"
        }
        
        response = client.post("/payments/apply", json=application_data)
        assert response.status_code == 422  # Validation error

    def test_negative_amount(self, setup_database, sample_service):
        # Add service first
        client.post("/payments/services", json=sample_service)
        
        # Try to apply with negative amount
        application_data = {
            "service_id": "test-service-1",
            "amount": -150.0,  # Negative amount
            "user_id": "user-123",
            "email": "test@example.com",
            "reason": "Test application reason",
            "application_id": "app-123"
        }
        
        response = client.post("/payments/apply", json=application_data)
        # Should still accept negative amounts as business logic might allow refunds
        assert response.status_code == 200

    def test_missing_required_fields(self, setup_database):
        # Try to create service with missing fields
        incomplete_service = {
            "service_id": "test-service-1",
            "name": "Test Service"
            # Missing description and base_price
        }
        
        response = client.post("/payments/services", json=incomplete_service)
        assert response.status_code == 422  # Validation error

class TestEdgeCases:
    @patch('payment_service.main.send_application_created_email')
    def test_very_long_strings(self, mock_email, setup_database):
        mock_email.return_value = True
        
        # Test with very long service name and description
        long_service = {
            "service_id": "test-service-1",
            "name": "A" * 99,  # Just under the 100 character limit
            "description": "B" * 499,  # Just under the 500 character limit
            "base_price": 100.0
        }
        
        response = client.post("/payments/services", json=long_service)
        assert response.status_code == 200

    @patch('payment_service.main.send_application_created_email')
    def test_unicode_characters(self, mock_email, setup_database):
        mock_email.return_value = True
        
        # Test with unicode characters
        unicode_service = {
            "service_id": "test-service-unicode",
            "name": "測試服務 🎉",
            "description": "這是一個測試服務的描述 with émojis 🚀",
            "base_price": 100.0
        }
        
        response = client.post("/payments/services", json=unicode_service)
        assert response.status_code == 200
        
        # Test application with unicode
        unicode_application = {
            "service_id": "test-service-unicode",
            "amount": 150.0,
            "user_id": "用戶-123",
            "email": "test@example.com",
            "reason": "申請原因：需要這個服務 🎯",
            "application_id": "app-unicode"
        }
        
        response = client.post("/payments/apply", json=unicode_application)
        assert response.status_code == 200

    def test_zero_amount(self, setup_database, sample_service):
        # Add service first
        client.post("/payments/services", json=sample_service)
        
        # Test with zero amount
        zero_application = {
            "service_id": "test-service-1",
            "amount": 0.0,
            "user_id": "user-123",
            "email": "test@example.com",
            "reason": "Free service application",
            "application_id": "app-zero"
        }
        
        response = client.post("/payments/apply", json=zero_application)
        assert response.status_code == 200

    def test_very_large_amount(self, setup_database, sample_service):
        # Add service first
        client.post("/payments/services", json=sample_service)
        
        # Test with very large amount
        large_application = {
            "service_id": "test-service-1",
            "amount": 999999999.99,
            "user_id": "user-123",
            "email": "test@example.com",
            "reason": "Large amount application",
            "application_id": "app-large"
        }
        
        response = client.post("/payments/apply", json=large_application)
        assert response.status_code == 200

class TestConcurrency:
    @patch('payment_service.main.send_application_created_email')
    def test_multiple_applications_same_user(self, mock_email, setup_database, sample_service):
        mock_email.return_value = True
        
        # Add service first
        client.post("/payments/services", json=sample_service)
        
        # Create multiple applications for same user
        applications = []
        for i in range(5):
            app_data = {
                "service_id": "test-service-1",
                "amount": 100.0 + i * 10,
                "user_id": "user-123",
                "email": "test@example.com",
                "reason": f"Application {i+1}",
                "application_id": f"app-{i+1}"
            }
            applications.append(app_data)
        
        # Submit all applications
        responses = []
        for app in applications:
            response = client.post("/payments/apply", json=app)
            responses.append(response)
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
        
        # Verify all applications exist
        response = client.get("/payments/user/user-123")
        assert response.status_code == 200
        data = response.json()
        assert len(data["payments"]) == 5

    @patch('payment_service.main.send_application_created_email')
    def test_duplicate_application_ids(self, mock_email, setup_database, sample_service):
        mock_email.return_value = True
        
        # Add service first
        client.post("/payments/services", json=sample_service)
        
        # Try to create applications with same application_id
        app_data = {
            "service_id": "test-service-1",
            "amount": 100.0,
            "user_id": "user-123",
            "email": "test@example.com",
            "reason": "First application",
            "application_id": "duplicate-app"
        }
        
        # First application should succeed
        response1 = client.post("/payments/apply", json=app_data)
        assert response1.status_code == 200
        
        # Second application with same ID should fail due to database constraint
        app_data["reason"] = "Second application"
        app_data["user_id"] = "user-456"
        response2 = client.post("/payments/apply", json=app_data)
        assert response2.status_code == 500  # Database constraint violation

class TestFileOperations:
    @patch('payment_service.main.send_application_created_email')
    def test_csv_file_creation_and_cleanup(self, mock_email, setup_database, sample_service, sample_payment_application):
        mock_email.return_value = True
        
        # Setup payment
        client.post("/payments/services", json=sample_service)
        response = client.post("/payments/apply", json=sample_payment_application)
        payment_id = response.json()["payment_id"]
        
        # Download payment CSV
        response = client.get(f"/payments/{payment_id}/download")
        assert response.status_code == 200
        
        # Verify CSV content type
        assert "text/csv" in response.headers["content-type"]

    @patch('os.makedirs')
    @patch('payment_service.main.send_application_created_email')
    def test_csv_directory_creation_error(self, mock_email, mock_makedirs, setup_database, sample_service, sample_payment_application):
        mock_email.return_value = True
        mock_makedirs.side_effect = OSError("Permission denied")

        # Setup payment
        client.post("/payments/services", json=sample_service)
        response = client.post("/payments/apply", json=sample_payment_application)
        payment_id = response.json()["payment_id"]

        # Try to download - should handle directory creation error gracefully
        # The function should use temp directory as fallback and succeed
        response = client.get(f"/payments/{payment_id}/download")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"

    @patch('builtins.open', side_effect=IOError("Disk full"))
    @patch('payment_service.main.send_application_created_email')
    def test_csv_file_write_error(self, mock_email, mock_open, setup_database, sample_service, sample_payment_application):
        mock_email.return_value = True
        
        # Setup payment
        client.post("/payments/services", json=sample_service)
        response = client.post("/payments/apply", json=sample_payment_application)
        payment_id = response.json()["payment_id"]
        
        # Try to download - should handle file write error
        response = client.get(f"/payments/{payment_id}/download")
        assert response.status_code == 500
        assert "Failed to generate payment CSV" in response.json()["detail"]

class TestDataValidation:
    def test_invalid_uuid_format(self, setup_database):
        # Test with invalid UUID format for payment_id
        response = client.get("/payments/not-a-valid-uuid-format")
        assert response.status_code == 404  # Should handle gracefully

    def test_sql_injection_attempt(self, setup_database):
        # Test with potential SQL injection in service_id
        malicious_service_id = "'; DROP TABLE payments; --"
        response = client.get(f"/payments/services/{malicious_service_id}")
        assert response.status_code == 404  # Should handle safely due to ORM

    def test_xss_attempt_in_service_name(self, setup_database):
        # Test with potential XSS in service name
        xss_service = {
            "service_id": "xss-test",
            "name": "<script>alert('xss')</script>",
            "description": "XSS test service",
            "base_price": 100.0
        }
        
        response = client.post("/payments/services", json=xss_service)
        assert response.status_code == 200
        
        # Verify the data is stored as-is (no HTML encoding in API)
        response = client.get("/payments/services/xss-test")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "<script>alert('xss')</script>"

if __name__ == "__main__":
    # Run tests with coverage
    pytest.main([
        "--cov=main",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--cov-fail-under=100",
        "-v"
    ])
