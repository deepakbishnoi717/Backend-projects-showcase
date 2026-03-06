"""
Logging Middleware
Adds structured logging with request_id, duration, and request details
"""
import time
import uuid
import logging
import json
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import config

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(message)s'
)
logger = logging.getLogger("ai_agent")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests with structured data"""
    
    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Start timer
        start_time = time.time()
        
        # Log request
        log_data = {
            "event": "request_started",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client_ip": request.client.host,
            "timestamp": time.time()
        }
        
        if config.LOG_FORMAT == "json":
            logger.info(json.dumps(log_data))
        else:
            logger.info(f"[{request_id}] {request.method} {request.url.path} from {request.client.host}")
        
        # Process request
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            # Log response
            log_data = {
                "event": "request_completed",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration * 1000, 2),
                "timestamp": time.time()
            }
            
            if config.LOG_FORMAT == "json":
                logger.info(json.dumps(log_data))
            else:
                logger.info(f"[{request_id}] {response.status_code} in {duration*1000:.2f}ms")
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Log error
            log_data = {
                "event": "request_failed",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "error": str(e),
                "duration_ms": round(duration * 1000, 2),
                "timestamp": time.time()
            }
            
            if config.LOG_FORMAT == "json":
                logger.error(json.dumps(log_data))
            else:
                logger.error(f"[{request_id}] Error: {str(e)} after {duration*1000:.2f}ms")
            
            raise
