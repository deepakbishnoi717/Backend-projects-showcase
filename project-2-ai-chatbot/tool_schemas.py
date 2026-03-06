"""
Day 14 — Tool API Pattern: Strict Pydantic Models
===================================================
These models guarantee that /tools/summarize and /tools/extract_json
always return data in the EXACT same JSON structure.

Why strict models?
- Without them, AI responses are unpredictable (sometimes string, sometimes dict)
- With response_model in FastAPI, the output is FORCED to match this schema
- If the output doesn't match, FastAPI returns a validation error (not garbage data)
"""

from pydantic import BaseModel, Field
from typing import Any, Dict, Optional


# ============================================================
# /tools/summarize — Request & Response Models
# ============================================================

class SummarizeRequest(BaseModel):
    """
    What the user sends to /tools/summarize.
    
    Strict rules:
    - text: Must be 10-10000 characters (no empty strings, no mega-texts)
    - max_words: Optional limit for summary length (between 10 and 500 words)
    """
    text: str = Field(
        ...,                          # ... means REQUIRED (can't skip this field)
        min_length=10,                # Minimum 10 characters (no empty/tiny inputs)
        max_length=10000,             # Maximum 10000 characters (prevents abuse)
        description="The text to summarize"
    )
    max_words: Optional[int] = Field(
        default=100,                  # Default summary length: 100 words
        ge=10,                        # ge = "greater than or equal to" (minimum 10)
        le=500,                       # le = "less than or equal to" (maximum 500)
        description="Maximum words in the summary"
    )


class SummarizeResponse(BaseModel):
    """
    What /tools/summarize ALWAYS returns.
    
    No matter what the AI says, the response will always have these exact fields.
    This makes the API predictable for any program consuming it.
    """
    summary: str = Field(
        ...,
        description="The summarized text"
    )
    original_length: int = Field(
        ...,
        ge=0,                         # Can't be negative
        description="Character count of the original text"
    )
    summary_length: int = Field(
        ...,
        ge=0,
        description="Character count of the summary"
    )
    model_used: str = Field(
        ...,
        description="Which AI model generated this summary"
    )


# ============================================================
# /tools/extract_json — Request & Response Models
# ============================================================

class ExtractJsonRequest(BaseModel):
    """
    What the user sends to /tools/extract_json.
    
    Strict rules:
    - text: Must be 5-5000 characters (the raw text to extract JSON from)
    - fields: Optional list of specific fields to extract
    
    Example use case:
      Input: "My name is John, I am 25 years old, email john@gmail.com"
      Output: {"name": "John", "age": 25, "email": "john@gmail.com"}
    """
    text: str = Field(
        ...,
        min_length=5,                 # At least 5 characters
        max_length=5000,              # Max 5000 characters
        description="The text to extract structured JSON from"
    )
    fields: Optional[str] = Field(
        default=None,
        max_length=500,               # Field hints can't be too long
        description="Optional: comma-separated list of fields to extract (e.g. 'name,age,email')"
    )


class ExtractJsonResponse(BaseModel):
    """
    What /tools/extract_json ALWAYS returns.
    
    'extracted_data' contains the actual JSON extracted from the text.
    'raw_response' contains the original AI response (for debugging).
    'success' tells you if the extraction worked.
    
    This strict schema means:
    - Programs can always access response.extracted_data
    - They don't need to guess the format
    - If extraction fails, success=False and error field explains why
    """
    extracted_data: Dict[str, Any] = Field(
        ...,
        description="The extracted JSON data"
    )
    raw_response: str = Field(
        ...,
        description="The raw AI response before parsing"
    )
    success: bool = Field(
        ...,
        description="Whether JSON extraction was successful"
    )
    model_used: str = Field(
        ...,
        description="Which AI model performed the extraction"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if extraction failed"
    )
