# Payment Service

This repository contains the Payment Service, a microservice designed to handle payment processing operations for the classroom booking system.

## Overview

The Payment Service provides a reliable way to process payments, manage transactions, and handle payment-related operations. It's built with FastAPI and designed to work as part of a microservices architecture.

## Getting Started

Follow these steps to set up and run the Payment Service on your local machine.

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Payment gateway API access (for processing payments)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd payment
```

2. **Create and activate a virtual environment**
```bash
# Create a virtual environment
python3 -m venv venv
# Activate the virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Create necessary directories**
```bash
mkdir -p logs csv_exports
```

### Running the Service

Start the Payment Service with:
```bash
uvicorn payment_service.main:app --reload --port 8000
```

The service will be available at `http://localhost:8000`.

## API Documentation

Once the service is running, you can access the API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Features

- Process payments through multiple payment gateways
- Transaction history and reporting
- Payment status tracking

## Testing

Run the tests with:
```bash
python3 -m pytest test/test_payment_service.py -v
```

## Project Structure

```
payment/
├── common_utils/      
│   ├── common_utils
│   │   ├── logger
│   │       ├── __init__.py
│   │       ├── client.py # client api for calling logger micro-service
│   │   ├── mailer
│   │       ├── __init__.py
│   │       ├── client.py # client api for calling mailer micro-service
│   ├── setup.py              
├── payment_service/       # Main package
│   ├── __init__.py
│   ├── main.py           # FastAPI application
├── tests/                # Test package
│   ├── __init__.py
│   └── test_payment.py   # Tests for payment service
├── .env                  # Environment variables (not in repo)
├── .gitignore            # Git ignore file
├── requirements.txt      # Project dependencies
└── README.md             # This file
```

## Notes

- This service is part of a larger microservices architecture including Mailer Service and Logger Service.
- When integrating with other services, you may need to adjust configurations accordingly.
- Ensure proper security measures are in place when handling payment information.

## License


## Contact
