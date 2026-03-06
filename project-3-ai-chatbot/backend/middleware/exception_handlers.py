"""
Global Exception Handlers
Standardized error responses for all exception types
"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging

logger = logging.getLogger("ai_agent")


async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with standardized format"""
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.warning(f"[{request_id}] HTTP {exc.status_code}: {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail if isinstance(exc.detail, str) else exc.detail.get("error", "Error"),
            "error_code": exc.detail.get("error_code", "HTTP_ERROR") if isinstance(exc.detail, dict) else "HTTP_ERROR",
            "details": exc.detail.get("details") if isinstance(exc.detail, dict) else None,
            "request_id": request_id
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed information"""
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.warning(f"[{request_id}] Validation error: {exc.errors()}")
    
    return JSONResponse(
        status_code=400,
        content={
            "error": "Validation failed",
            "error_code": "VALIDATION_ERROR",
            "details": exc.errors(),
            "request_id": request_id
        }
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions gracefully"""
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.error(f"[{request_id}] Unhandled exception: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "error_code": "INTERNAL_ERROR",
            "details": {"message": str(exc)},
            "request_id": request_id
        }
    )


async def timeout_exception_handler(request: Request, exc: TimeoutError):
    """Handle timeout errors with friendly message"""
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.warning(f"[{request_id}] Request timeout")
    
    return JSONResponse(
        status_code=504,
        content={
            "error": "Request timed out. The AI took too long to respond.",
            "error_code": "TIMEOUT_ERROR",
            "details": {"message": "Please try again with a simpler question or reduce the complexity."},
            "request_id": request_id
        }
    )
