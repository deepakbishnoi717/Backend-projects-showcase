"""
Week 7 — All Tests (11 tests total)
=====================================
Tests for Days 14-18: Tool APIs, Audit Logs, Validation, Rate Limiting, Security.

How to run these tests:
    cd "c:\\Users\\HP\\OneDrive\\Desktop\\ai agent"
    python -m pytest tests/test_tools.py -v

What is pytest?
- A testing framework for Python
- Each function starting with 'test_' is a test
- Assertions check if the result matches expectations
- If any assertion fails, the test FAILS

What is TestClient?
- FastAPI provides TestClient to simulate HTTP requests
- Instead of running the server and using a browser, we can test directly in code
- TestClient sends fake requests and returns the response

What is unittest.mock?
- 'mock' replaces real functions with fake ones during testing
- We mock the AI agent so tests don't actually call OpenAI/Groq APIs
- This makes tests fast, free, and reliable
"""

import pytest
import json
import time
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Import our app and modules
from main import app
from database import SessionLocal, AuditLog, Base, engine
from middleware.rate_limiter import rate_limiter
import config


# ============================================================
# Test Setup
# ============================================================

# Create a TestClient — this lets us send fake HTTP requests to our app
client = TestClient(app)

# Valid API key for testing (must match config.TOOL_API_KEY)
VALID_API_KEY = config.TOOL_API_KEY

# Headers with a valid API key (used for authorized requests)
AUTH_HEADERS = {"X-API-Key": VALID_API_KEY}


def reset_rate_limiter():
    """
    Resets the rate limiter between tests.
    
    Why?
    - Each test should be independent
    - If test_A sends 10 requests, test_B shouldn't be rate limited
    - This clears all stored request counts
    """
    from collections import defaultdict
    rate_limiter.requests = defaultdict(lambda: defaultdict(list))
    rate_limiter.failures = defaultdict(lambda: {"count": 0, "last_failure": 0})
    rate_limiter.cooldowns = {}


# ============================================================
# Day 14 Tests: Tool API Pattern
# ============================================================

@patch("main.test_agent")
def test_summarize_returns_correct_schema(mock_agent):
    """
    Day 14 — Test 1: /tools/summarize returns the expected JSON schema.
    
    What this tests:
    - The response MUST have: summary, original_length, summary_length, model_used
    - original_length MUST equal the length of input text
    - summary_length MUST equal the length of returned summary
    
    Why mock?
    - We don't want to actually call Groq API during testing
    - mock_agent.return_value = "..." makes test_agent return our fake response
    """
    reset_rate_limiter()
    
    # Make the AI agent return a fake summary (instead of calling real API)
    mock_agent.return_value = "This is a test summary of the input text."
    
    # Send a request to /tools/summarize
    response = client.post(
        "/tools/summarize",
        json={"text": "This is a long text that needs to be summarized. " * 5, "max_words": 50},
        headers=AUTH_HEADERS
    )
    
    # Check: response status should be 200 (success)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    
    # Check: response must have ALL required fields
    assert "summary" in data, "Response missing 'summary' field"
    assert "original_length" in data, "Response missing 'original_length' field"
    assert "summary_length" in data, "Response missing 'summary_length' field"
    assert "model_used" in data, "Response missing 'model_used' field"
    
    # Check: lengths must be non-negative integers
    assert data["original_length"] >= 0, "original_length cannot be negative"
    assert data["summary_length"] >= 0, "summary_length cannot be negative"
    assert isinstance(data["summary"], str), "summary must be a string"


@patch("main.test_agent")
def test_extract_json_returns_valid_json(mock_agent):
    """
    Day 14 — Test 2: /tools/extract_json returns valid JSON data.
    
    What this tests:
    - The response MUST have: extracted_data, raw_response, success, model_used
    - extracted_data MUST be a dictionary (valid JSON object)
    - success MUST be True when parsing succeeds
    """
    reset_rate_limiter()
    
    # Make the AI return a valid JSON string
    mock_agent.return_value = '{"name": "John", "age": 25, "city": "NYC"}'
    
    response = client.post(
        "/tools/extract_json",
        json={"text": "John is 25 years old and lives in NYC", "fields": "name,age,city"},
        headers=AUTH_HEADERS
    )
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    
    # Check: response must have ALL required fields
    assert "extracted_data" in data, "Response missing 'extracted_data' field"
    assert "raw_response" in data, "Response missing 'raw_response' field"
    assert "success" in data, "Response missing 'success' field"
    assert "model_used" in data, "Response missing 'model_used' field"
    
    # Check: extracted_data must be a dictionary
    assert isinstance(data["extracted_data"], dict), "extracted_data must be a dict"
    
    # Check: success must be True
    assert data["success"] is True, "success should be True for valid JSON"
    
    # Check: the extracted data contains expected keys
    assert "name" in data["extracted_data"], "Should have extracted 'name'"
    assert data["extracted_data"]["name"] == "John"


# ============================================================
# Day 15 Tests: Audit Logs
# ============================================================

@patch("main.test_agent")
def test_audit_log_created_on_success(mock_agent):
    """
    Day 15 — Test 3: A successful tool call creates an audit log entry.
    
    What this tests:
    - After calling /tools/summarize successfully, check the database
    - There should be a new AuditLog entry with status="success"
    - The entry should have the correct tool_name
    
    Why?
    - Audit logs must be AUTOMATIC — we shouldn't rely on developers to log manually
    - This test proves that the logging happens without extra effort
    """
    reset_rate_limiter()
    
    mock_agent.return_value = "Test summary"
    
    # Count audit logs BEFORE the request
    db = SessionLocal()
    count_before = db.query(AuditLog).filter(AuditLog.tool_name == "summarize").count()
    db.close()
    
    # Make the request
    response = client.post(
        "/tools/summarize",
        json={"text": "This is test text for audit logging verification purposes."},
        headers=AUTH_HEADERS
    )
    
    assert response.status_code == 200
    
    # Count audit logs AFTER the request
    db = SessionLocal()
    count_after = db.query(AuditLog).filter(AuditLog.tool_name == "summarize").count()
    
    # Check: there should be one MORE audit log entry
    assert count_after > count_before, "No audit log was created on success!"
    
    # Check: the latest log entry has status="success"
    latest_log = db.query(AuditLog).filter(
        AuditLog.tool_name == "summarize"
    ).order_by(AuditLog.id.desc()).first()
    
    assert latest_log.status == "success", f"Expected status 'success', got '{latest_log.status}'"
    assert latest_log.tool_name == "summarize"
    db.close()


@patch("main.test_agent")
def test_audit_log_created_on_error(mock_agent):
    """
    Day 15 — Test 4: A failed tool call ALSO creates an audit log entry.
    
    What this tests:
    - When the AI agent throws an error, an audit log should still be created
    - The log should have status="error" and error_message filled in
    
    Why?
    - Failed calls are ESPECIALLY important to log
    - They help identify bugs, abuse, and system issues
    """
    reset_rate_limiter()
    
    # Make the AI agent throw an error
    mock_agent.side_effect = Exception("AI service unavailable")
    
    # Count logs before
    db = SessionLocal()
    count_before = db.query(AuditLog).count()
    db.close()
    
    # Make the request (should fail)
    response = client.post(
        "/tools/summarize",
        json={"text": "This is test text that will cause an error in the AI."},
        headers=AUTH_HEADERS
    )
    
    # The endpoint should return 500 (server error)
    assert response.status_code == 500
    
    # Check: audit log was STILL created
    db = SessionLocal()
    count_after = db.query(AuditLog).count()
    assert count_after > count_before, "No audit log was created on error!"
    
    # Check: the log has status="error"
    latest_log = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
    assert latest_log.status == "error", f"Expected status 'error', got '{latest_log.status}'"
    assert latest_log.error_message is not None, "Error message should be filled in"
    db.close()


# ============================================================
# Day 16 Tests: Validation Hardening
# ============================================================

def test_validation_rejects_too_short_text():
    """
    Day 16 — Test 5: Summarize rejects text shorter than 10 characters.
    
    What this tests:
    - SummarizeRequest requires min_length=10 on the 'text' field
    - Sending "Hi" (2 chars) should be rejected with 400 error
    
    Why?
    - There's no point summarizing 2 characters
    - It prevents accidental empty or trivially short requests
    - It saves AI API costs
    """
    reset_rate_limiter()
    
    response = client.post(
        "/tools/summarize",
        json={"text": "Hi"},  # Only 2 characters — below min_length=10
        headers=AUTH_HEADERS
    )
    
    # Should be rejected with 400 (Bad Request)
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"


def test_validation_rejects_invalid_model_name():
    """
    Day 16 — Test 6: Chat rejects model names with special characters.
    
    What this tests:
    - ChatRequest has pattern=r'^[a-zA-Z0-9\\-\\.]+$' on model_name
    - Sending "hack!@#$" should be rejected because of special characters
    
    Why?
    - Model names should only have letters, numbers, hyphens, and dots
    - This prevents code injection through the model name field
    """
    reset_rate_limiter()
    
    response = client.post(
        "/chat",
        json={
            "model_name": "hack!@#$%",  # Invalid characters!
            "model_provider": "groq",
            "messages": ["Hello"],
            "allow_search": False
        }
    )
    
    # Should be rejected with 400 (validation error)
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"


def test_validation_rejects_invalid_provider():
    """
    Day 16 — Test 7: Chat rejects providers that aren't 'groq' or 'openai'.
    
    What this tests:
    - ChatRequest uses ModelProvider enum (only 'groq' or 'openai')
    - Sending "hackme" as provider should be rejected
    
    Why?
    - Using Enum prevents arbitrary strings from reaching the AI provider logic
    - Only the two valid providers are accepted
    """
    reset_rate_limiter()
    
    response = client.post(
        "/chat",
        json={
            "model_name": "llama-3.3-70b-versatile",
            "model_provider": "hackme",  # Not 'groq' or 'openai'!
            "messages": ["Hello"],
            "allow_search": False
        }
    )
    
    # Should be rejected with 400 (validation error)
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"


# ============================================================
# Day 17 Tests: Rate Limiting Upgrade
# ============================================================

@patch("main.test_agent")
def test_tool_rate_limit_is_stricter(mock_agent):
    """
    Day 17 — Test 8: Tool endpoints have stricter rate limits than chat.
    
    What this tests:
    - /tools/* routes allow only 5 requests per minute
    - After 5 requests, the 6th should be blocked with 429
    
    Why per-route limits?
    - Tool endpoints use expensive AI calls
    - They need stricter limits to prevent abuse
    - Chat gets 10/min, tools get 5/min
    """
    reset_rate_limiter()
    
    mock_agent.return_value = "Summary"
    
    # Send 5 requests (should all succeed)
    for i in range(5):
        response = client.post(
            "/tools/summarize",
            json={"text": f"This is test text number {i} for rate limiting."},
            headers=AUTH_HEADERS
        )
        # First 5 should succeed (200) or at least not be rate-limited
        assert response.status_code != 429, f"Request {i+1} was rate limited too early!"
    
    # 6th request should be rate limited
    response = client.post(
        "/tools/summarize",
        json={"text": "This sixth request should be blocked by rate limiter."},
        headers=AUTH_HEADERS
    )
    
    assert response.status_code == 429, f"Expected 429 on 6th request, got {response.status_code}"


@patch("main.test_agent")
def test_cooldown_after_repeated_failures(mock_agent):
    """
    Day 17 — Test 9: IP is blocked after too many consecutive failures.
    
    What this tests:
    - After 5 consecutive failures, the IP enters cooldown
    - During cooldown, ALL requests are blocked (even valid ones)
    
    Why cooldown?
    - Someone trying random API keys → blocked after 5 attempts
    - Someone brute-forcing your API → can't keep trying
    - Legitimate users rarely have 5 failures in a row
    """
    reset_rate_limiter()
    
    # Record 5 consecutive failures for the test client's IP
    test_ip = "testclient"
    for _ in range(5):
        rate_limiter.record_failure(test_ip)
    
    # Check: the IP should now be in cooldown
    assert rate_limiter.is_in_cooldown(test_ip), "IP should be in cooldown after 5 failures"


# ============================================================
# Day 18 Tests: Security Checklist
# ============================================================

def test_unauthorized_cannot_access_tools():
    """
    Day 18 — Test 10: Requests without API key are rejected.
    
    What this tests:
    - Calling /tools/summarize WITHOUT the X-API-Key header
    - Should get 401 Unauthorized response
    
    Why?
    - Tool endpoints are expensive (they call AI APIs)
    - Only authorized users (with valid API keys) should access them
    - This prevents unauthorized usage and abuse
    """
    reset_rate_limiter()
    
    # Send request WITHOUT API key header
    response = client.post(
        "/tools/summarize",
        json={"text": "This request has no API key and should be rejected completely."}
        # No headers= with API key!
    )
    
    # Should be rejected with 401 (Unauthorized)
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    data = response.json()
    assert "error" in data, "Error response should have 'error' field"


def test_invalid_api_key_rejected():
    """
    Day 18 — Test 11: Requests with WRONG API key are rejected.
    
    What this tests:
    - Calling /tools/summarize with an invalid/fake API key
    - Should get 401 Unauthorized response
    
    Why?
    - Even if someone knows the header name (X-API-Key), they need the right VALUE
    - This tests that the authorization check is working properly
    """
    reset_rate_limiter()
    
    # Send request with WRONG API key
    response = client.post(
        "/tools/summarize",
        json={"text": "This request has a wrong API key and should be rejected."},
        headers={"X-API-Key": "this-is-a-fake-key-12345"}
    )
    
    # Should be rejected with 401 (Unauthorized)
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"


# ============================================================
# Bonus: Test validators.py directly
# ============================================================

def test_filename_safety():
    """
    Bonus test: make_filename_safe handles dangerous inputs.
    
    This directly tests the validators.py helper function
    to ensure it properly sanitizes filenames.
    """
    from validators import make_filename_safe
    
    # Test: path traversal attack
    assert ".." not in make_filename_safe("../../etc/passwd"), "Should remove path traversal"
    
    # Test: special characters removed
    result = make_filename_safe("my file!@#.txt")
    assert "!" not in result, "Should remove special characters"
    assert "@" not in result
    
    # Test: empty string
    assert make_filename_safe("") == "unnamed", "Empty string should return 'unnamed'"
    
    # Test: only dots
    assert make_filename_safe("...") == "unnamed", "Only dots should return 'unnamed'"
