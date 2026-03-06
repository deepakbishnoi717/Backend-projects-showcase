from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from enum import Enum


class ModelProvider(str, Enum):
    """Restricts model_provider to valid values only."""
    GROQ = "groq"
    OPENAI = "openai"


class ChatRequest(BaseModel):
    """Request model for /chat endpoint with strict validation."""

    model_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r'^[a-zA-Z0-9\-\.]+$',
        description="AI model name (e.g. 'gpt-4o-mini', 'llama-3.3-70b-versatile')"
    )

    model_provider: ModelProvider = Field(
        ...,
        description="AI provider — must be 'groq' or 'openai'"
    )

    system_prompt: str = Field(
        default="You are a helpful AI assistant",
        min_length=0,
        max_length=1000,
        description="Instructions for the AI's behavior"
    )

    messages: List[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="List of user messages"
    )

    allow_search: bool = Field(
        default=False,
        description="Whether to allow web search via Tavily"
    )

    @field_validator('messages')
    @classmethod
    def validate_message_length(cls, v):
        """Validates each message is between 1 and 2000 characters."""
        for i, msg in enumerate(v):
            if len(msg) < 1:
                raise ValueError(f"Message {i+1} cannot be empty")
            if len(msg) > 2000:
                raise ValueError(
                    f"Message {i+1} too long ({len(msg)} chars). Maximum is 2000 characters."
                )
        return v


class ChatResponse(BaseModel):
    """Standard response model for /chat endpoint."""
    response: str
    request_id: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standardized error response."""
    error: str
    error_code: str
    details: Optional[dict] = None
    request_id: Optional[str] = None