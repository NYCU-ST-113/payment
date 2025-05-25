# logger_client.py
import requests
import os
from datetime import datetime
from typing import Dict, Any, Optional

class LoggerClient:
    def __init__(self, service_name, logger_url=None):
        self.service_name = service_name
        self.logger_url = logger_url or os.environ.get("LOGGER_SERVICE_URL", "http://localhost:7000")
    
    def _send_log(self, level, message, details=None):
        try:
            log_data = {
                "service": self.service_name,
                "level": level,
                "message": message,
                "timestamp": datetime.now().isoformat(),
            }
            
            if details:
                log_data["details"] = details
                
            response = requests.post(f"{self.logger_url}/log", json=log_data, timeout=2)
            return response.status_code == 200
        except Exception as e:
            # If the logging service is unavailable, output to console
            print(f"Error sending log to logger service: {str(e)}")
            print(f"{level} - {message} - {details}")
            return False
    
    def info(self, message, details=None):
        return self._send_log("INFO", message, details)
    
    def error(self, message, details=None):
        return self._send_log("ERROR", message, details)
    
    def warning(self, message, details=None):
        return self._send_log("WARNING", message, details)
    
    def debug(self, message, details=None):
        return self._send_log("DEBUG", message, details)
