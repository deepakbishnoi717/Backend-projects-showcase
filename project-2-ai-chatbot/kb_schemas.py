from pydantic import BaseModel, Field
from typing import List, Optional


class FileUploadResult(BaseModel):

    document_id: int = Field(..., description="Unique ID of the uploaded document")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., ge=0, description="File size in bytes")
    status: str = Field(..., description="Processing status: uploaded/processing/ready/error")
    message: str = Field(..., description="Human-readable status message")


class TextChunkDetail(BaseModel):

    chunk_id: int = Field(..., description="Unique chunk ID")
    chunk_index: int = Field(..., ge=0, description="Position in the document (0-based)")
    content: str = Field(..., description="The text content of this chunk")
    document_id: int = Field(..., description="ID of the parent document")


class QueryInput(BaseModel):

    q: str = Field(..., min_length=1, max_length=500, description="Search query")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results to return")


class MatchedChunk(BaseModel):

    chunk_id: int = Field(..., description="ID of the matching chunk")
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score (0-1)")
    content: str = Field(..., description="Text content of the chunk")
    filename: str = Field(..., description="Name of the source document")


class QueryResult(BaseModel):

    query: str = Field(..., description="The original search query")
    results: List[MatchedChunk] = Field(..., description="Matching chunks ranked by relevance")
    total_results: int = Field(..., ge=0, description="Number of results returned")


class QuestionInput(BaseModel):

    question: str = Field(..., min_length=3, max_length=1000, description="The question to answer")
    top_k: int = Field(default=5, ge=1, le=10, description="Number of context chunks to use")


class QuestionAnswer(BaseModel):

    answer: str = Field(..., description="AI-generated answer")
    model_used: str = Field(..., description="Which AI model generated the answer")

