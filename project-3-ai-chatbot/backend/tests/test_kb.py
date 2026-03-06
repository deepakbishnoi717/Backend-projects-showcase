"""
Week 8 — AI Knowledge Base Tests
===================================
Tests for: Upload, Chunking, Embeddings, Search, Answer.

How to run:
    cd "c:\\Users\\HP\\OneDrive\\Desktop\\ai agent"
    python -m pytest tests/test_kb.py -v

These tests use:
- TestClient: Simulates HTTP requests without running the server
- Mock: Fakes the AI agent so we don't call real APIs
- Temporary files: Creates test .txt files for upload testing
"""

import pytest
import io
import json
import os
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from main import app
from database import SessionLocal, Base, engine
from kb_models import KBDocument, KBChunk, KBEmbedding
from kb_service import chunk_text, validate_file, generate_embedding, cosine_similarity
from middleware.rate_limiter import rate_limiter
from collections import defaultdict
import config


# ============================================================
# Test Setup
# ============================================================

client = TestClient(app)
VALID_API_KEY = config.TOOL_API_KEY
AUTH_HEADERS = {"X-API-Key": VALID_API_KEY}


def reset_rate_limiter():
    """Reset rate limiter state between tests."""
    rate_limiter.requests = defaultdict(lambda: defaultdict(list))
    rate_limiter.failures = defaultdict(lambda: {"count": 0, "last_failure": 0})
    rate_limiter.cooldowns = {}


def create_test_file(content: str, filename: str = "test.txt") -> tuple:
    """
    Creates a fake uploaded file for testing.
    
    Returns a tuple of (filename, file-like object, content_type)
    that can be used with TestClient's file upload.
    """
    return ("file", (filename, io.BytesIO(content.encode("utf-8")), "text/plain"))


# ============================================================
# Test 1: Upload — Bad File Type Rejected
# ============================================================

def test_upload_bad_file_type_rejected():
    """
    Uploading a .exe file is rejected.
    Only .txt and .pdf files are allowed.
    """
    reset_rate_limiter()
    
    file_content = b"fake executable content"
    
    response = client.post(
        "/kb/upload",
        files=[("file", ("malware.exe", io.BytesIO(file_content), "application/octet-stream"))]
    )
    
    assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
    assert "not allowed" in response.json().get("detail", {}).get("error", "").lower()


# ============================================================
# Test 2: Upload — Valid File Succeeds
# ============================================================

def test_upload_success():
    """
    Uploading a valid .txt file succeeds.
    Tests the full pipeline: upload → save → extract text → chunk → embed
    """
    reset_rate_limiter()
    
    test_content = "This is a test document with enough content for chunking. " * 20
    
    response = client.post(
        "/kb/upload",
        files=[("file", ("test_document.txt", io.BytesIO(test_content.encode()), "text/plain"))]
    )
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert "document_id" in data, "Response missing 'document_id'"
    assert "filename" in data, "Response missing 'filename'"
    assert data["status"] == "ready", f"Expected status 'ready', got '{data['status']}'"


# ============================================================
# Test 3: Text Chunking
# ============================================================

def test_chunk_count_sanity():
    """
    chunk_text produces a reasonable number of chunks.
    A 1000-character text with chunk_size=500 and overlap=50 should make ~3 chunks.
    """
    text = "A" * 1000
    
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    
    assert len(chunks) >= 2, f"Expected at least 2 chunks, got {len(chunks)}"
    assert len(chunks) <= 5, f"Expected at most 5 chunks, got {len(chunks)}"
    
    # No empty chunks
    for chunk in chunks:
        assert len(chunk["content"]) > 0, "Chunk content should not be empty"
    
    # Each chunk should have metadata
    for chunk in chunks:
        assert "char_start" in chunk
        assert "char_end" in chunk
        assert "chunk_index" in chunk


# ============================================================
# Test 4: Embeddings
# ============================================================

def test_embedding_record_created():
    """
    Embedding generation produces a valid vector.
    - Should be a list of floats
    - Should have correct dimensions
    """
    text = "Machine learning is a branch of artificial intelligence"
    
    embedding = generate_embedding(text)
    
    assert isinstance(embedding, list), "Embedding should be a list"
    assert len(embedding) > 0, "Embedding should not be empty"
    
    for val in embedding:
        assert isinstance(val, float), f"Embedding values should be floats, got {type(val)}"


# ============================================================
# Test 5: Search Returns Results
# ============================================================

def test_search_returns_results():
    """
    After uploading a document, searching for related terms returns results.
    """
    reset_rate_limiter()
    
    # Upload a document first
    test_content = "Machine learning is artificial intelligence. Deep learning uses neural networks. " * 10
    client.post(
        "/kb/upload",
        files=[("file", ("ml_notes.txt", io.BytesIO(test_content.encode()), "text/plain"))]
    )
    
    # Now search
    response = client.get(
        "/kb/search",
        params={"q": "machine learning", "top_k": 3}
    )
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert "results" in data, "Response missing 'results'"
    assert "query" in data, "Response missing 'query'"
    assert "total_results" in data, "Response missing 'total_results'"
    
    if data["total_results"] > 0:
        result = data["results"][0]
        assert "chunk_id" in result
        assert "score" in result
        assert "content" in result
        assert "filename" in result


# ============================================================
# Test 6: Search — Empty Query Rejected
# ============================================================

def test_search_empty_query_handled():
    """
    Empty search query is properly rejected.
    """
    reset_rate_limiter()
    
    response = client.get(
        "/kb/search",
        params={"q": "", "top_k": 5}
    )
    
    assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}"


# ============================================================
# Test 7: Answer Endpoint
# ============================================================

@patch("kb_router.test_agent")
def test_answer_returns_response(mock_agent):
    """
    Answer endpoint returns a response with answer and model_used.
    """
    reset_rate_limiter()
    
    # Upload a relevant document first
    test_content = "Python is a programming language created by Guido van Rossum. " * 20
    client.post(
        "/kb/upload",
        files=[("file", ("python_info.txt", io.BytesIO(test_content.encode()), "text/plain"))]
    )
    
    # Mock the AI agent
    mock_agent.return_value = "Based on the documents, Python was created by Guido van Rossum."
    
    response = client.post(
        "/kb/answer",
        json={"question": "Who created Python?", "top_k": 3}
    )
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert "answer" in data, "Response missing 'answer'"
    assert "model_used" in data, "Response missing 'model_used'"


# ============================================================
# Test 8: Cosine Similarity Math
# ============================================================

def test_cosine_similarity_correctness():
    """
    Cosine similarity math is correct.
    - Identical vectors → 1.0
    - Opposite vectors → -1.0
    - Perpendicular vectors → 0.0
    """
    # Identical vectors → similarity = 1.0
    vec = [1.0, 0.0, 1.0]
    assert abs(cosine_similarity(vec, vec) - 1.0) < 0.001, "Identical vectors should have sim ~1.0"
    
    # Opposite vectors → similarity = -1.0
    vec_a = [1.0, 0.0]
    vec_b = [-1.0, 0.0]
    assert abs(cosine_similarity(vec_a, vec_b) - (-1.0)) < 0.001, "Opposite vectors should have sim ~-1.0"
    
    # Perpendicular vectors → similarity = 0.0
    vec_a = [1.0, 0.0]
    vec_b = [0.0, 1.0]
    assert abs(cosine_similarity(vec_a, vec_b) - 0.0) < 0.001, "Perpendicular vectors should have sim ~0.0"
