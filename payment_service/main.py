from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import FileResponse 
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import csv
import os
import requests
from common_utils.logger.client import LoggerClient
from common_utils.mailer.client import MailerClient

# Database related imports
from sqlalchemy import create_engine, Column, String, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
import pymysql
pymysql.install_as_MySQLdb()

app = FastAPI()
logger = LoggerClient("payment-service")
EMAIL_SERVICE_URL = os.environ.get("EMAIL_SERVICE_URL", "http://localhost:6000")

mailer = MailerClient("payment-service", EMAIL_SERVICE_URL)

# Database configuration
DATABASE_URL = os.environ.get("DATABASE_URL", "mysql://user:password@localhost:3306/appdb")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency function to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Database models
class PaymentServiceModel(Base):
    __tablename__ = "payment_services"
    
    service_id = Column(String(36), primary_key=True, index=True)
    name = Column(String(100), index=True)
    description = Column(String(500))
    base_price = Column(Float)
    
    # Relationships
    payments = relationship("PaymentModel", back_populates="service")

class PaymentModel(Base):
    __tablename__ = "payments"
    
    payment_id = Column(String(36), primary_key=True, index=True)
    service_id = Column(String(36), ForeignKey("payment_services.service_id"))
    amount = Column(Float)
    user_id = Column(String(36), index=True)
    status = Column(String(20))  # "pending", "paid", "failed"
    created_at = Column(DateTime)
    email = Column(String(100))
    
    # Relationships
    service = relationship("PaymentServiceModel", back_populates="payments")

class PaymentApplicationModel(Base):
    __tablename__ = "payment_applications"
    
    application_id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), index=True)
    service_id = Column(String(36), ForeignKey("payment_services.service_id"))
    amount = Column(Float)
    reason = Column(String(500))
    status = Column(String(20))  # "pending", "approved", "rejected"
    created_at = Column(DateTime)
    email = Column(String(100))
    
    # Relationships
    service = relationship("PaymentServiceModel")

# Create database tables
Base.metadata.create_all(bind=engine)

# model definition
class PaymentService(BaseModel):
    service_id: str
    name: str
    description: str
    base_price: float

class PaymentServiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    base_price: Optional[float] = None

class PaymentCreate(BaseModel):
    service_id: str
    amount: float
    user_id: str
    email: EmailStr

class PaymentStatus(BaseModel):
    payment_id: str
    status: str
    amount: float
    created_at: str

class Payment(BaseModel):
    payment_id: str
    service_id: str
    amount: float
    user_id: str
    status: str # "pending", "paid", "failed"
    created_at: datetime
    email: EmailStr

class PaymentUpdate(BaseModel):
    status: str

class MessageResponse(BaseModel):
    message: str

class PaymentApplication(BaseModel):
    user_id: str
    service_id: str
    amount: float
    reason: str
    email: EmailStr
    
class PaymentApplicationResponse(BaseModel):
    application_id: str
    status: str
    created_at: str

class PaymentProcessRequest(BaseModel):
    transaction_id: Optional[str] = None

def send_payment_created_email(payment_id: str, email: str, service_name: str, amount: float, due_date: str):
    try:
        mailer.send_template_email(
            to_email=email,
            template_id="payment_created",
            template_data={
                "payment_id": payment_id,
                "service_name": service_name,
                "amount": amount,
                "due_date": due_date
            }
        )
        logger.info(f"Payment created email sent to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send payment created email: {str(e)}")
        return False

def send_payment_success_email(payment_id: str, email: str, service_name: str, amount: float, transaction_id: Optional[str] = None):
    try:
        template_data = {
            "payment_id": payment_id,
            "service_name": service_name,
            "amount": amount
        }
        
        if transaction_id:
            template_data["transaction_id"] = transaction_id
            
        mailer.send_template_email(
            to_email=email,
            template_id="payment_success",
            template_data=template_data
        )
        logger.info(f"Payment success email sent to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send payment success email: {str(e)}")
        return False

def send_payment_failed_email(payment_id: str, email: str, service_name: str, amount: float, reason: str):
    try:
        mailer.send_template_email(
            to_email=email,
            template_id="payment_failed",
            template_data={
                "payment_id": payment_id,
                "service_name": service_name,
                "amount": amount,
                "reason": reason
            }
        )
        logger.info(f"Payment failed email sent to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send payment failed email: {str(e)}")
        return False

def send_application_created_email(application_id: str, email: str, service_name: str, amount: float):
    try:
        mailer.send_template_email(
            to_email=email,
            template_id="application_created",
            template_data={
                "application_id": application_id,
                "service_name": service_name,
                "amount": amount
            }
        )
        logger.info(f"Application created email sent to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send application created email: {str(e)}")
        return False

def send_application_approved_email(application_id: str, email: str, service_name: str, amount: float, payment_id: str):
    try:
        mailer.send_template_email(
            to_email=email,
            template_id="application_approved",
            template_data={
                "application_id": application_id,
                "service_name": service_name,
                "amount": amount,
                "payment_id": payment_id
            }
        )
        logger.info(f"Application approved email sent to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send application approved email: {str(e)}")
        return False

def send_application_rejected_email(application_id: str, email: str, service_name: str, amount: float, reason: str):
    try:
        mailer.send_template_email(
            to_email=email,
            template_id="application_rejected",
            template_data={
                "application_id": application_id,
                "service_name": service_name,
                "amount": amount,
                "reason": reason
            }
        )
        logger.info(f"Application rejected email sent to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send application rejected email: {str(e)}")
        return False

def send_application_deleted_email(application_id: str, email: str, service_name: str, amount: float):
    try:
        mailer.send_template_email(
            to_email=email,
            template_id="application_deleted",
            template_data={
                "application_id": application_id,
                "service_name": service_name,
                "amount": amount
            }
        )
        logger.info(f"Application deleted email sent to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send application deleted email: {str(e)}")
        return False

# Routes
@app.get("/")
def read_root():
    return {"status": "ok", "service": "payment-service"}

# payment service related nodes
@app.get("/payments/services")
async def list_payment_services(db: Session = Depends(get_db)):
    logger.info("Listing all payment services", {})
    services = db.query(PaymentServiceModel).all()
    return services

@app.get("/payments/services/{service_id}")
async def get_payment_service(service_id: str, db: Session = Depends(get_db)):
    logger.info(f"Getting payment service details", {"service_id": service_id})
    service = db.query(PaymentServiceModel).filter(PaymentServiceModel.service_id == service_id).first()
    if not service:
        logger.warning(f"Payment service not found", {"service_id": service_id})
        raise HTTPException(status_code=404, detail="Payment service not found")
    logger.debug(f"Payment service found", {"service_id": service_id, "service_name": service.name})
    return service

@app.post("/payments/services")
async def add_payment_service(service: PaymentService, db: Session = Depends(get_db)):
    logger.info(f"Adding new payment service", {"service_id": service.service_id, "name": service.name})
    
    # Check if service already exists
    existing_service = db.query(PaymentServiceModel).filter(
        PaymentServiceModel.service_id == service.service_id
    ).first()
    
    if existing_service:
        logger.warning(f"Service ID already exists", {"service_id": service.service_id})
        raise HTTPException(status_code=400, detail="Service ID already exists")
    
    # Create new service
    db_service = PaymentServiceModel(
        service_id=service.service_id,
        name=service.name,
        description=service.description,
        base_price=service.base_price
    )
    
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    
    logger.info(f"Payment service added successfully", {"service_id": service.service_id})
    return db_service

@app.put("/payments/services/{service_id}") 
async def update_payment_service(service_id: str, service_update: PaymentServiceUpdate, db: Session = Depends(get_db)):
    logger.info(f"Updating payment service", {"service_id": service_id})
    
    db_service = db.query(PaymentServiceModel).filter(
        PaymentServiceModel.service_id == service_id
    ).first()
    
    if not db_service:
        logger.warning(f"Payment service not found", {"service_id": service_id})
        raise HTTPException(status_code=404, detail="Payment service not found")
    
    update_data = service_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_service, field, value)
    
    db.commit()
    db.refresh(db_service)
    
    logger.info(f"Payment service updated successfully", {"service_id": service_id, "updated_fields": list(update_data.keys())})
    return db_service

@app.delete("/payments/services/{service_id}")
async def delete_payment_service(service_id: str, db: Session = Depends(get_db)):
    logger.info(f"Deleting payment service", {"service_id": service_id})
    
    db_service = db.query(PaymentServiceModel).filter(
        PaymentServiceModel.service_id == service_id
    ).first()
    
    if not db_service:
        logger.warning(f"Payment service not found", {"service_id": service_id})
        raise HTTPException(status_code=404, detail="Payment service not found")
    
    db.delete(db_service)
    db.commit()
    
    logger.info(f"Payment service deleted successfully", {"service_id": service_id})
    return {"message": "Payment service deleted successfully"}


# payment order related nodes
@app.get("/payments")
async def list_all_payments(db: Session = Depends(get_db)):
    """Get all payment records"""
    logger.info("Listing all payments")
    
    db_payments = db.query(PaymentModel).all()
    all_payments = []
    
    for payment in db_payments:
        service_name = "Unknown Service"
        db_service = db.query(PaymentServiceModel).filter(
            PaymentServiceModel.service_id == payment.service_id
        ).first()
        
        if db_service:
            service_name = db_service.name
        
        all_payments.append({
            "payment_id": payment.payment_id,
            "service_id": payment.service_id,
            "service_name": service_name,
            "amount": payment.amount,
            "user_id": payment.user_id,
            "status": payment.status,
            "created_at": payment.created_at.isoformat(),
            "email": payment.email
        })
    
    return {"payments": all_payments}

@app.post("/payments/create")
async def create_payment(payment: PaymentCreate, db: Session = Depends(get_db)):
    payment_id = str(uuid.uuid4())
    logger.info(f"Creating new payment", {"payment_id": payment_id, "user_id": payment.user_id})
    
    try:
        # Check if service exists
        db_service = db.query(PaymentServiceModel).filter(
            PaymentServiceModel.service_id == payment.service_id
        ).first()
        
        if not db_service:
            logger.warning(f"Service not found for payment", {"payment_id": payment_id, "service_id": payment.service_id})
            raise HTTPException(status_code=404, detail="Service not found")
        
        # Create new payment order
        new_payment = PaymentModel(
            payment_id=payment_id,
            service_id=payment.service_id,
            amount=payment.amount,
            user_id=payment.user_id,
            status="pending",
            created_at=datetime.now(),
            email=payment.email
        )
        
        db.add(new_payment)
        db.commit()
        db.refresh(new_payment)
        
        # Prepare to send email
        service_name = db_service.name
        due_date = new_payment.created_at + timedelta(days=30)
        due_date_str = due_date.strftime("%Y-%m-%d")
        
        # Send email notification
        success = send_payment_created_email(
            payment_id=str(payment_id),
            email=new_payment.email,
            service_name=service_name,
            amount=float(new_payment.amount),
            due_date=due_date_str
        )
        
        if not success:
            logger.warning("Failed to send email notification", {"payment_id": payment_id, "email": new_payment.email})
        
        # Log successful payment creation
        logger.info(f"Payment created for user {payment.user_id}", {
            "payment_id": payment_id,
            "amount": payment.amount,
            "service_id": payment.service_id
        })
        
        return {
            "payment_id": payment_id,
            "status": "pending",
            "amount": new_payment.amount,
            "created_at": new_payment.created_at.isoformat()
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create payment: {str(e)}", {
            "user_id": payment.user_id,
            "service_id": payment.service_id,
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail="Failed to create payment")

@app.get("/payments/{payment_id}/info")
async def get_payment_info(payment_id: str, db: Session = Depends(get_db)):
    logger.info(f"Getting payment info", {"payment_id": payment_id})
    
    payment = db.query(PaymentModel).filter(
        PaymentModel.payment_id == payment_id
    ).first()
    
    if not payment:
        logger.warning(f"Payment not found", {"payment_id": payment_id})
        raise HTTPException(status_code=404, detail="Payment not found")
    
    return {
        "payment_id": payment.payment_id,
        "status": payment.status,
        "amount": payment.amount,
        "created_at": payment.created_at.isoformat()
    }

@app.put("/payments/{payment_id}")
async def update_payment(payment_id: str, payment_update: PaymentUpdate, db: Session = Depends(get_db)):
    logger.info(f"Updating payment status", {"payment_id": payment_id, "new_status": payment_update.status})
    
    payment = db.query(PaymentModel).filter(
        PaymentModel.payment_id == payment_id
    ).first()
    
    if not payment:
        logger.warning(f"Payment not found", {"payment_id": payment_id})
        raise HTTPException(status_code=404, detail="Payment not found")
    
    payment.status = payment_update.status
    db.commit()
    db.refresh(payment)

    # Get service name
    service_name = "Unknown Service"
    db_service = db.query(PaymentServiceModel).filter(
        PaymentServiceModel.service_id == payment.service_id
    ).first()
    
    if db_service:
        service_name = db_service.name
    
    if payment.status == "paid":
        logger.info(f"Payment marked as paid", {"payment_id": payment_id})
        # Send payment success email
        success = send_payment_success_email(
            payment_id=payment_id,
            email=payment.email,
            service_name=service_name,
            amount=payment.amount
        )
        
        if not success:
            logger.warning("Failed to send payment success email", {"payment_id": payment_id, "email": payment.email})
    
    elif payment.status == "failed":
        logger.info(f"Payment marked as failed", {"payment_id": payment_id})
        # Send payment failure email
        success = send_payment_failed_email(
            payment_id=payment_id,
            email=payment.email,
            service_name=service_name,
            amount=payment.amount,
            reason="Payment processing failed"
        )
        
        if not success:
            logger.warning("Failed to send payment failure email", {"payment_id": payment_id, "email": payment.email})
    
    return payment

@app.post("/payments/{payment_id}/process")
async def process_payment(payment_id: str, request: PaymentProcessRequest = None, db: Session = Depends(get_db)):
    payment = db.query(PaymentModel).filter(
        PaymentModel.payment_id == payment_id
    ).first()
    
    if not payment:
        logger.warning(f"Payment not found", {"payment_id": payment_id})
        raise HTTPException(status_code=404, detail="Payment not found")
    
    # Simulate payment processing
    payment.status = "paid"
    db.commit()
    db.refresh(payment)
    
    # Get service name
    service_name = "Unknown Service"
    db_service = db.query(PaymentServiceModel).filter(
        PaymentServiceModel.service_id == payment.service_id
    ).first()
    
    if db_service:
        service_name = db_service.name
    
    # Send email notification
    transaction_id = request.transaction_id if request and request.transaction_id else str(uuid.uuid4())
    success = send_payment_success_email(
        payment_id=payment_id,
        email=payment.email,
        service_name=service_name,
        amount=payment.amount,
        transaction_id=transaction_id
    )
    
    if not success:
        logger.warning("Failed to send payment success email", {"payment_id": payment_id, "email": payment.email})
    
    return {
        "payment_id": payment.payment_id,
        "status": payment.status,
        "amount": payment.amount,
        "created_at": payment.created_at.isoformat()
    }

@app.post("/payments/{payment_id}/fail")
async def fail_payment(payment_id: str, db: Session = Depends(get_db)):
    payment = db.query(PaymentModel).filter(
        PaymentModel.payment_id == payment_id
    ).first()
    
    if not payment:
        logger.warning(f"Payment not found", {"payment_id": payment_id})
        raise HTTPException(status_code=404, detail="Payment not found")
    
    payment.status = "failed"
    db.commit()
    db.refresh(payment)
    
    # Get service name
    service_name = "Unknown Service"
    db_service = db.query(PaymentServiceModel).filter(
        PaymentServiceModel.service_id == payment.service_id
    ).first()
    
    if db_service:
        service_name = db_service.name
    
    # Send email notification
    success = send_payment_failed_email(
        payment_id=payment_id,
        email=payment.email,
        service_name=service_name,
        amount=payment.amount,
        reason="Payment processing failed"
    )
    
    if not success:
        logger.warning("Failed to send payment failure email", {"payment_id": payment_id, "email": payment.email})
    
    return {
        "payment_id": payment.payment_id,
        "status": payment.status,
        "amount": payment.amount,
        "created_at": payment.created_at.isoformat()
    }

@app.delete("/payments/{payment_id}")
async def delete_payment(payment_id: str, db: Session = Depends(get_db)):
    logger.info(f"Deleting payment", {"payment_id": payment_id})
    
    payment = db.query(PaymentModel).filter(
        PaymentModel.payment_id == payment_id
    ).first()
    
    if not payment:
        logger.warning(f"Payment not found", {"payment_id": payment_id})
        raise HTTPException(status_code=404, detail="Payment not found")
    
    db.delete(payment)
    db.commit()
    
    logger.info(f"Payment deleted successfully", {"payment_id": payment_id})
    return {"message": "Payment deleted successfully"}

@app.post("/payments/apply")
async def apply_payment(application: PaymentApplication, db: Session = Depends(get_db)):
    logger.info(f"Received payment application", {"user_id": application.user_id, "service_id": application.service_id})
    
    application_id = str(uuid.uuid4())
    
    # Check if service exists
    db_service = db.query(PaymentServiceModel).filter(
        PaymentServiceModel.service_id == application.service_id
    ).first()
    
    if not db_service:
        logger.warning(f"Payment service not found", {"service_id": application.service_id})
        raise HTTPException(status_code=404, detail="Payment service not found")
    
    # Create application record
    db_application = PaymentApplicationModel(
        application_id=application_id,
        user_id=application.user_id,
        service_id=application.service_id,
        amount=application.amount,
        reason=application.reason,
        status="pending",
        created_at=datetime.now(),
        email=application.email
    )
    
    db.add(db_application)
    db.commit()
    db.refresh(db_application)

    # Get service name
    service_name = db_service.name
    
    # Send email notification
    success = send_application_created_email(
        application_id=application_id,
        email=application.email,
        service_name=service_name,
        amount=application.amount
    )
    
    if not success:
        logger.warning("Failed to send email notification", {"application_id": application_id, "email": application.email})
    
    logger.info(f"Payment application created", {"application_id": application_id, "status": "pending"})
    return PaymentApplicationResponse(
        application_id=application_id,
        status="pending",
        created_at=db_application.created_at.isoformat()
    )

@app.get("/payments/applications/{application_id}")
async def get_application_info(application_id: str, db: Session = Depends(get_db)):
    """Get application status"""
    logger.info(f"Getting application info", {"application_id": application_id})
    
    application = db.query(PaymentApplicationModel).filter(
        PaymentApplicationModel.application_id == application_id
    ).first()
    
    if not application:
        logger.warning(f"Application not found", {"application_id": application_id})
        raise HTTPException(status_code=404, detail="Application not found")

    return {
        "application_id": application_id,
        "status": application.status,
        "created_at": application.created_at.isoformat()
    }

@app.put("/payments/applications/{application_id}/approve")
async def approve_application(application_id: str, db: Session = Depends(get_db)):
    """Approve payment application"""
    logger.info(f"Approving payment application", {"application_id": application_id})
    
    application = db.query(PaymentApplicationModel).filter(
        PaymentApplicationModel.application_id == application_id
    ).first()
    
    if not application:
        logger.warning(f"Application not found", {"application_id": application_id})
        raise HTTPException(status_code=404, detail="Application not found")
    
    application.status = "approved"
    db.commit()
    db.refresh(application)
    
    # Create corresponding payment record
    payment_id = str(uuid.uuid4())
    new_payment = PaymentModel(
        payment_id=payment_id,
        service_id=application.service_id,
        amount=application.amount,
        user_id=application.user_id,
        status="pending",
        created_at=datetime.now(),
        email=application.email
    )
    
    db.add(new_payment)
    db.commit()
    db.refresh(new_payment)

    # Get service name
    service_name = "Unknown Service"
    db_service = db.query(PaymentServiceModel).filter(
        PaymentServiceModel.service_id == application.service_id
    ).first()
    
    if db_service:
        service_name = db_service.name
    
    # Send email notification
    success = send_application_approved_email(
        application_id=application_id,
        email=application.email,
        service_name=service_name,
        amount=application.amount,
        payment_id=payment_id
    )
    
    if not success:
        logger.warning("Failed to send application approved email", {"application_id": application_id, "email": application.email})
    
    # Send payment creation email
    due_date = new_payment.created_at + timedelta(days=30)
    due_date_str = due_date.strftime("%Y-%m-%d")
    
    send_payment_created_email(
        payment_id=payment_id,
        email=application.email,
        service_name=service_name,
        amount=application.amount,
        due_date=due_date_str
    )
    
    logger.info(f"Application approved and payment created", 
                {"application_id": application_id, "payment_id": payment_id, "status": "pending"})
    
    return {
        "message": "Application approved and payment created",
        "payment_id": payment_id,
        "status": "pending"
    }

@app.put("/payments/applications/{application_id}/reject")
async def reject_application(application_id: str, reason: str, db: Session = Depends(get_db)):
    """Reject payment application"""
    logger.info(f"Rejecting payment application", {"application_id": application_id, "reason": reason})
    
    application = db.query(PaymentApplicationModel).filter(
        PaymentApplicationModel.application_id == application_id
    ).first()
    
    if not application:
        logger.warning(f"Application not found", {"application_id": application_id})
        raise HTTPException(status_code=404, detail="Application not found")

    application.status = "rejected"
    db.commit()
    db.refresh(application)

    # Get service name
    service_name = "Unknown Service"
    db_service = db.query(PaymentServiceModel).filter(
        PaymentServiceModel.service_id == application.service_id
    ).first()
    
    if db_service:
        service_name = db_service.name
                
    # Send email notification
    success = send_application_rejected_email(
        application_id=application_id,
        email=application.email,
        service_name=service_name,
        amount=application.amount,
        reason=reason
    )
    
    if not success:
        logger.warning("Failed to send application rejected email", {"application_id": application_id, "email": application.email})
    
    logger.info(f"Application rejected", {"application_id": application_id})
    return {"message": "Application rejected"}

@app.delete("/payments/applications/{application_id}")
async def delete_application(application_id: str, db: Session = Depends(get_db)):
    """Delete payment application"""
    logger.info(f"Deleting payment application", {"application_id": application_id})
    
    application = db.query(PaymentApplicationModel).filter(
        PaymentApplicationModel.application_id == application_id
    ).first()
    
    if not application:
        logger.warning(f"Application not found", {"application_id": application_id})
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Save application info for email
    email = application.email
    amount = application.amount
    service_id = application.service_id
    
    # Get service name
    service_name = "Unknown Service"
    db_service = db.query(PaymentServiceModel).filter(
        PaymentServiceModel.service_id == service_id
    ).first()
    
    if db_service:
        service_name = db_service.name
    
    db.delete(application)
    db.commit()
    
    # Send email notification
    success = send_application_deleted_email(
        application_id=application_id,
        email=email,
        service_name=service_name,
        amount=amount
    )
    
    if not success:
        logger.warning("Failed to send application deleted email", {"application_id": application_id, "email": email})
    
    logger.info(f"Payment application successfully deleted", {"application_id": application_id})
    return {"message": "Payment application successfully deleted"}

# Download payment information endpoint - CSV format
@app.get("/payments/{payment_id}/download")
async def download_payment(payment_id: str, db: Session = Depends(get_db)):
    """Download payment information in CSV format"""
    logger.info(f"Downloading payment information", {"payment_id": payment_id})
    
    payment = db.query(PaymentModel).filter(
        PaymentModel.payment_id == payment_id
    ).first()
    
    if not payment:
        logger.warning(f"Payment not found", {"payment_id": payment_id})
        raise HTTPException(status_code=404, detail="Payment not found")
    
    # Get service name (if exists)
    service_name = "Unknown Service"
    db_service = db.query(PaymentServiceModel).filter(
        PaymentServiceModel.service_id == payment.service_id
    ).first()
    
    if db_service:
        service_name = db_service.name
    
    # Create CSV file
    # Configure CSV directory, similar to log directory
    CSV_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'csv_exports')
    os.makedirs(CSV_DIR, exist_ok=True)
    
    # Create date-based subdirectory for better organization
    date_dir = os.path.join(CSV_DIR, datetime.now().strftime("%Y-%m-%d"))
    os.makedirs(date_dir, exist_ok=True)
    
    # Create CSV file path
    file_path = os.path.join(date_dir, f"payment_{payment_id}.csv")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    logger.debug(f"Creating CSV file", {"file_path": file_path})
    
    try:
        with open(file_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            
            writer.writerow([
                "Payment ID", "Service ID", "Service Name", "Amount",
                "User ID", "Status", "Created At"
            ])
            
            # Write header row
            writer.writerow([
                payment.payment_id,
                payment.service_id,
                service_name,
                payment.amount,
                payment.user_id,
                payment.status,
                payment.created_at.isoformat()
            ])
        
        logger.info(f"CSV file created successfully", {"payment_id": payment_id, "file_path": file_path})
            
        # Return file download response
        return FileResponse(
            path=file_path,
            filename=f"payment_{payment_id}.csv",
            media_type="text/csv"
        )
    except Exception as e:
        logger.error(f"Failed to create CSV file", {
            "payment_id": payment_id,
            "error": str(e),
            "file_path": file_path
        })
        raise HTTPException(status_code=500, detail="Failed to generate payment CSV")

@app.get("/export/payments")
async def export_payments(db: Session = Depends(get_db)):
    """Export all payments to CSV file"""
    logger.info("Exporting all payments to CSV")
    
    # Create CSV file
    CSV_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'csv_exports')
    os.makedirs(CSV_DIR, exist_ok=True)
    
    # Create date-based filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(CSV_DIR, f"all_payments_{timestamp}.csv")
    
    try:
        with open(file_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            
            # Write header row
            writer.writerow([
                "Payment ID", "Service ID", "Service Name", "Amount",
                "User ID", "Status", "Created At", "Email"
            ])
            
            # Query all payments
            payments = db.query(PaymentModel).all()
            
            # Write data rows
            for payment in payments:
                service_name = "Unknown Service"
                db_service = db.query(PaymentServiceModel).filter(
                    PaymentServiceModel.service_id == payment.service_id
                ).first()
                
                if db_service:
                    service_name = db_service.name
                
                writer.writerow([
                    payment.payment_id,
                    payment.service_id,
                    service_name,
                    payment.amount,
                    payment.user_id,
                    payment.status,
                    payment.created_at.isoformat(),
                    payment.email
                ])
        
        logger.info(f"All payments exported successfully", {"file_path": file_path})
        
        # Return file download response
        return FileResponse(
            path=file_path,
            filename=f"all_payments_{timestamp}.csv",
            media_type="text/csv"
        )
    except Exception as e:
        logger.error(f"Failed to export payments", {"error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to export payments")
