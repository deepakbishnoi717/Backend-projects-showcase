"""
AI Agent API — Main Application (Week 7: Guardrails Complete)
==============================================================
This is the main FastAPI application file that ties everything together.

What's in this file:
- Day 14: /tools/summarize and /tools/extract_json endpoints
- Day 15: Audit logging on every tool call (success + error)
- Day 16: Validation hardening (strict models from schema.py)
- Day 17: Rate limiting middleware (per-route, from rate_limiter.py)
- Day 18: CORS configuration + API key authorization on tool routes

How FastAPI works:
1. A request comes in (e.g. POST /tools/summarize)
2. Middleware runs first (logging → rate limiting → CORS)
3. Dependencies run (verify_api_key checks authorization)
4. Pydantic validates the request body (rejects bad input)
5. The endpoint function runs (calls AI, creates audit log)
6. Response model validates the output (guarantees format)
7. Response is sent back to the user
"""

import json
import uuid

from fastapi import FastAPI, Request, HTTPException, Depends, Header
from fastapi.responses import StreamingResponse, RedirectResponse, FileResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Our modules
from schema import ChatRequest, ChatResponse, ErrorResponse
from tool_schemas import (
    SummarizeRequest, SummarizeResponse,
    ExtractJsonRequest, ExtractJsonResponse
)
from backend import test_agent, stream_agent_response
from database import get_db, log_tool_call
from validators import sanitize_text_input
from kb_router import kb_router  # Week 8: Knowledge Base router
import config

# Middleware imports
from middleware.rate_limiter import RateLimitMiddleware
from middleware.logging_middleware import LoggingMiddleware
from middleware.exception_handlers import (
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
    timeout_exception_handler
)


# ============================================================
# App Initialization
# ============================================================

app = FastAPI(
    title="AI Agent API",
    version="2.0.0",
    description="AI Agent with Guardrails: Tool APIs, Audit Logs, Validation, Rate Limits, and Security"
)


# ============================================================
# Day 18: CORS Middleware
# ============================================================
# 
# What is CORS?
# When your frontend (http://localhost:3000) calls your API (http://localhost:8000),
# the browser blocks this by default because they're on different "origins" (ports).
# CORSMiddleware tells the browser: "It's okay, I trust these origins."
#
# IMPORTANT: In production, NEVER use allow_origins=["*"]
# That would let ANY website in the world call your API!

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,         # Only these frontends can call us
    allow_credentials=True,                     # Allow cookies/auth headers
    allow_methods=["GET", "POST"],              # Only GET and POST (not DELETE, PUT, etc.)
    allow_headers=["Content-Type", "X-API-Key", "Authorization"],  # Allowed headers
)

# Add our custom middleware (order matters!)
# Logging runs first (outer), then rate limiting (inner)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)

# Register exception handlers
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(TimeoutError, timeout_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Week 8: Include Knowledge Base router
# All /kb/* endpoints (upload, search, answer) are defined in kb_router.py
app.include_router(kb_router)

# Serve static files (UI)
app.mount("/ui", StaticFiles(directory="../frontend", html=True), name="static")


# ============================================================
# Allowed AI Models
# ============================================================

allowed_models = [
    # Llama Models (Meta) — Free on Groq
    "llama-3.3-70b-versatile",
    "llama-3.1-70b-versatile",
    "llama3-70b-8192",
    "llama3-8b-8192",
    # Mixtral Models (Mistral AI) — Free on Groq
    "mixtral-8x7b-32768",
    # Gemma Models (Google) — Free on Groq
    "gemma2-9b-it",
    "gemma-7b-it",
    # OpenAI Models (Requires billing)
    "gpt-4o-mini",
]


# ============================================================
# Day 18: API Key Authorization (AuthZ)
# ============================================================

async def verify_api_key(x_api_key: str = Header(None)):
    """
    Security dependency: Checks if the user has a valid API key.
    
    How it works:
    1. User sends a request with header: X-API-Key: their-secret-key
    2. FastAPI extracts the header value automatically (Header(None))
    3. We compare it against the valid key from config
    4. If missing or invalid → 401 Unauthorized (request blocked)
    5. If valid → return the key (request proceeds)
    
    Why Header(None) instead of Header(...)?
    - Header(...) would make it required and show a different error
    - Header(None) makes it optional, so we can give a custom "missing key" message
    
    Usage in endpoints:
        @app.post("/tools/summarize")
        async def summarize(api_key: str = Depends(verify_api_key)):
            # This endpoint now REQUIRES a valid API key
            # If the key is missing/invalid, this function never runs
    
    The 'Depends(verify_api_key)' tells FastAPI:
        "Before running this endpoint, run verify_api_key first"
    """
    # Check if API key header was provided
    if x_api_key is None:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "Missing API key",
                "error_code": "AUTH_MISSING",
                "details": {"message": "Include X-API-Key header in your request"}
            }
        )
    
    # Check if the API key is valid
    if x_api_key != config.TOOL_API_KEY:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "Invalid API key",
                "error_code": "AUTH_INVALID",
                "details": {"message": "The provided API key is not valid"}
            }
        )
    
    return x_api_key


# ============================================================
# Health Check Endpoint
# ============================================================

@app.get("/")
def root():
    """Redirect to the UI."""
    return RedirectResponse(url="/ui")


@app.get("/health")
def health():
    """Health check endpoint for monitoring systems."""
    return {
        "status": "ok",
        "service": "AI Agent API",
        "version": "2.0.0",
        "guardrails": "active"
    }


# ============================================================
# Chat Endpoints (existing)
# ============================================================

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, req: Request):
    """
    Normal chat endpoint — returns complete AI response.
    
    No API key required (general access).
    Rate limited: 10 requests/minute.
    """
    request_id = getattr(req.state, "request_id", str(uuid.uuid4()))
    
    if request.model_name not in allowed_models:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Invalid model name",
                "error_code": "INVALID_MODEL",
                "details": {"allowed_models": allowed_models},
                "request_id": request_id
            }
        )
    
    response = test_agent(
        llm_id=request.model_name,
        query=request.messages,
        allow_search=request.allow_search,
        system_prompt=request.system_prompt,
        provider=request.model_provider
    )

    return ChatResponse(response=response, request_id=request_id)


@app.post("/ai/chat/stream")
async def chat_stream(request: ChatRequest, req: Request):
    """
    Streaming chat endpoint — returns response chunk-by-chunk using SSE.
    
    No API key required (general access).
    Rate limited: 10 requests/minute.
    """
    request_id = getattr(req.state, "request_id", str(uuid.uuid4()))
    
    if request.model_name not in allowed_models:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Invalid model name",
                "error_code": "INVALID_MODEL",
                "details": {"allowed_models": allowed_models},
                "request_id": request_id
            }
        )
    
    async def event_generator():
        """Generate Server-Sent Events"""
        try:
            async for chunk in stream_agent_response(
                llm_id=request.model_name,
                query=request.messages,
                allow_search=request.allow_search,
                system_prompt=request.system_prompt,
                provider=request.model_provider
            ):
                yield chunk
        except Exception as e:
            yield f"data: {{\"error\": \"{str(e)}\", \"request_id\": \"{request_id}\"}}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Request-ID": request_id
        }
    )


# ============================================================
# Day 14: Tool Endpoints (NEW)
# Day 15: With Audit Logging
# Day 18: With API Key Authorization
# ============================================================

@app.post("/tools/summarize", response_model=SummarizeResponse)
async def summarize_text(
    request: SummarizeRequest,                  # Day 14: Strict input validation
    req: Request,
    api_key: str = Depends(verify_api_key),     # Day 18: Requires API key
    db: Session = Depends(get_db)               # Day 15: Database session for audit log
):
    """
    Tool Endpoint: Summarize Text
    
    Day 14 — Tool API Pattern:
        - Takes text input, sends it to AI for summarization
        - ALWAYS returns SummarizeResponse format (guaranteed by response_model)
        - If the AI returns something unexpected, Pydantic catches it
    
    Day 15 — Audit Logging:
        - Every call is logged to the audit_logs table
        - On success: logs the summary
        - On error: logs the error message
    
    Day 18 — Security:
        - Requires X-API-Key header (verified by verify_api_key dependency)
        - Without a valid key, this endpoint returns 401
    
    Rate Limit: 5 requests/minute (from rate_limiter.py)
    
    Example request:
        POST /tools/summarize
        Headers: X-API-Key: your-key-here
        Body: {"text": "Long article text here...", "max_words": 50}
    
    Example response:
        {
            "summary": "Short version of the article",
            "original_length": 5000,
            "summary_length": 200,
            "model_used": "llama-3.3-70b-versatile"
        }
    """
    # Get client IP for audit log
    client_ip = req.client.host if req.client else "unknown"
    
    # Sanitize input (Day 16: validation hardening)
    clean_text = sanitize_text_input(request.text)
    
    # Model to use for summarization
    model_name = "llama-3.3-70b-versatile"
    
    try:
        # Call the AI to summarize the text
        prompt = f"Summarize the following text in no more than {request.max_words} words. Return ONLY the summary, no extra text:\n\n{clean_text}"
        
        summary = test_agent(
            llm_id=model_name,
            query=[prompt],
            allow_search=False,
            system_prompt="You are a precise text summarizer. Return only the summary.",
            provider="groq"
        )
        
        # Build the response (Day 14: strict schema)
        result = SummarizeResponse(
            summary=summary,
            original_length=len(clean_text),
            summary_length=len(summary),
            model_used=model_name
        )
        
        # Day 15: Log SUCCESS to audit table
        log_tool_call(
            db=db,
            tool_name="summarize",
            input_data=clean_text[:500],           # Store first 500 chars (don't store huge texts)
            output_data=summary[:500],
            status="success",
            user_id="api_key_user",
            ip_address=client_ip
        )
        
        return result
        
    except Exception as e:
        # Day 15: Log ERROR to audit table
        log_tool_call(
            db=db,
            tool_name="summarize",
            input_data=clean_text[:500],
            output_data=None,
            status="error",
            error_message=str(e),
            user_id="api_key_user",
            ip_address=client_ip
        )
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Summarization failed",
                "error_code": "TOOL_ERROR",
                "details": {"message": str(e)}
            }
        )


@app.post("/tools/extract_json", response_model=ExtractJsonResponse)
async def extract_json_from_text(
    request: ExtractJsonRequest,                # Day 14: Strict input validation
    req: Request,
    api_key: str = Depends(verify_api_key),     # Day 18: Requires API key
    db: Session = Depends(get_db)               # Day 15: Database session for audit log
):
    """
    Tool Endpoint: Extract JSON from Text
    
    Day 14 — Tool API Pattern:
        - Takes unstructured text, asks AI to extract structured JSON
        - ALWAYS returns ExtractJsonResponse format
        - If AI can't extract valid JSON, returns success=False with error
    
    Day 15 — Audit Logging:
        - Every call logged (success and failure)
    
    Day 18 — Security:
        - Requires X-API-Key header
    
    Rate Limit: 5 requests/minute
    
    Example request:
        POST /tools/extract_json
        Headers: X-API-Key: your-key-here
        Body: {"text": "John is 25 years old and lives in NYC", "fields": "name,age,city"}
    
    Example response:
        {
            "extracted_data": {"name": "John", "age": 25, "city": "NYC"},
            "raw_response": "{\"name\": \"John\", ...}",
            "success": true,
            "model_used": "llama-3.3-70b-versatile",
            "error": null
        }
    """
    client_ip = req.client.host if req.client else "unknown"
    
    # Sanitize input (Day 16)
    clean_text = sanitize_text_input(request.text)
    
    model_name = "llama-3.3-70b-versatile"
    
    # Build the prompt
    # If user specified fields, ask AI to extract those specific fields
    if request.fields:
        prompt = f"""Extract the following fields from the text and return ONLY valid JSON (no markdown, no explanation):

Fields to extract: {request.fields}

Text: {clean_text}

Return format: {{"field1": "value1", "field2": "value2"}}"""
    else:
        prompt = f"""Extract all key information from the text and return ONLY valid JSON (no markdown, no explanation):

Text: {clean_text}

Return format: {{"key1": "value1", "key2": "value2"}}"""
    
    try:
        # Call the AI to extract JSON
        raw_response = test_agent(
            llm_id=model_name,
            query=[prompt],
            allow_search=False,
            system_prompt="You are a JSON extraction tool. Return ONLY valid JSON, no markdown, no explanation, no code blocks.",
            provider="groq"
        )
        
        # Try to parse the AI's response as JSON
        # The AI might return: {"name": "John", "age": 25}
        # Or it might return: ```json\n{"name": "John"}\n```
        # We need to handle both cases
        try:
            # Clean the response — remove markdown code blocks if present
            cleaned_response = raw_response.strip()
            
            # Remove ```json ... ``` wrapping if present
            if cleaned_response.startswith("```"):
                lines = cleaned_response.split("\n")
                # Remove first line (```json) and last line (```)
                cleaned_response = "\n".join(lines[1:-1])
            
            # Parse as JSON
            extracted_data = json.loads(cleaned_response)
            
            result = ExtractJsonResponse(
                extracted_data=extracted_data,
                raw_response=raw_response,
                success=True,
                model_used=model_name,
                error=None
            )
            
            # Day 15: Log SUCCESS
            log_tool_call(
                db=db,
                tool_name="extract_json",
                input_data=clean_text[:500],
                output_data=json.dumps(extracted_data),
                status="success",
                user_id="api_key_user",
                ip_address=client_ip
            )
            
            return result
            
        except json.JSONDecodeError as json_err:
            # AI returned something that's not valid JSON
            result = ExtractJsonResponse(
                extracted_data={},
                raw_response=raw_response,
                success=False,
                model_used=model_name,
                error=f"AI response was not valid JSON: {str(json_err)}"
            )
            
            # Day 15: Log as ERROR (extraction failed)
            log_tool_call(
                db=db,
                tool_name="extract_json",
                input_data=clean_text[:500],
                output_data=raw_response[:500],
                status="error",
                error_message=f"JSON parse failed: {str(json_err)}",
                user_id="api_key_user",
                ip_address=client_ip
            )
            
            return result
            
    except Exception as e:
        # Day 15: Log ERROR
        log_tool_call(
            db=db,
            tool_name="extract_json",
            input_data=clean_text[:500],
            output_data=None,
            status="error",
            error_message=str(e),
            user_id="api_key_user",
            ip_address=client_ip
        )
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "JSON extraction failed",
                "error_code": "TOOL_ERROR",
                "details": {"message": str(e)}
            }
        )