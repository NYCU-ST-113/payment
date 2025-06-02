FROM python:3.11-slim

WORKDIR /app

COPY . .
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p logs csv_exports

EXPOSE 8000
CMD ["uvicorn", "payment_service.main:app", "--host", "0.0.0.0", "--port", "8000"]

