import json
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request, Query
from sqlalchemy.orm import Session

from database import get_db, log_tool_call
from kb_models import KBDocument, KBChunk, KBEmbedding
from kb_schemas import (
    FileUploadResult, QueryInput, QueryResult, MatchedChunk,
    QuestionInput, QuestionAnswer
)
from kb_service import (
    validate_file, save_uploaded_file, extract_text_from_file,
    chunk_text, store_chunks, process_document_embeddings,
    search_chunks
)
from validators import make_filename_safe
from backend import test_agent
import config


kb_router = APIRouter(prefix="/kb", tags=["Knowledge Base"])


@kb_router.post("/upload", response_model=FileUploadResult)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a file to the Knowledge Base. Validates, saves, chunks, and embeds."""
    client_ip = request.client.host if request.client else "unknown"

    content = await file.read()
    file_size = len(content)

    is_valid, error_msg = validate_file(file.filename, file_size)
    if not is_valid:
        log_tool_call(
            db=db, tool_name="kb_upload",
            input_data=file.filename, status="error",
            error_message=error_msg, ip_address=client_ip
        )
        raise HTTPException(
            status_code=400,
            detail={"error": error_msg, "error_code": "INVALID_FILE"}
        )

    file_type = file.filename.rsplit(".", 1)[-1].lower()

    try:
        file_path = save_uploaded_file(file.filename, content)

        safe_name = make_filename_safe(file.filename)
        document = KBDocument(
            filename=file.filename,
            safe_filename=safe_name,
            file_type=file_type,
            file_size=file_size,
            file_path=file_path,
            status="processing"
        )
        db.add(document)
        db.commit()
        db.refresh(document)

        raw_text = extract_text_from_file(file_path, file_type)

        if not raw_text or not raw_text.strip():
            document.status = "error"
            db.commit()
            raise HTTPException(
                status_code=400,
                detail={"error": "Could not extract text from file", "error_code": "EXTRACTION_FAILED"}
            )

        chunks = chunk_text(raw_text)
        chunk_count = store_chunks(db, document.id, chunks)

        embedding_count = process_document_embeddings(db, document.id)

        document.status = "ready"
        document.chunk_count = chunk_count
        db.commit()

        log_tool_call(
            db=db, tool_name="kb_upload",
            input_data=f"filename={file.filename}, size={file_size}",
            output_data=f"chunks={chunk_count}, embeddings={embedding_count}",
            status="success", ip_address=client_ip
        )

        return FileUploadResult(
            document_id=document.id,
            filename=file.filename,
            file_size=file_size,
            status="ready",
            message=f"File uploaded and processed successfully. Created {chunk_count} chunks with {embedding_count} embeddings."
        )

    except HTTPException:
        raise
    except Exception as e:
        log_tool_call(
            db=db, tool_name="kb_upload",
            input_data=file.filename, status="error",
            error_message=str(e), ip_address=client_ip
        )
        raise HTTPException(
            status_code=500,
            detail={"error": f"Upload processing failed: {str(e)}", "error_code": "PROCESSING_ERROR"}
        )


@kb_router.get("/search", response_model=QueryResult)
async def search_knowledge_base(
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    top_k: int = Query(default=5, ge=1, le=20, description="Number of results"),
    db: Session = Depends(get_db),
):
    """Search the Knowledge Base for relevant chunks using semantic similarity."""
    if not q.strip():
        raise HTTPException(
            status_code=400,
            detail={"error": "Search query cannot be empty", "error_code": "EMPTY_QUERY"}
        )

    results = search_chunks(db, q, top_k)

    search_results = [
        MatchedChunk(
            chunk_id=r["chunk_id"],
            score=r["score"],
            content=r["content"],
            filename=r["source"]["filename"]
        )
        for r in results
    ]

    return QueryResult(
        query=q,
        results=search_results,
        total_results=len(search_results)
    )


@kb_router.post("/answer", response_model=QuestionAnswer)
async def answer_question(
    request: QuestionInput,
    req: Request,
    db: Session = Depends(get_db),
):
    """Answer a question using RAG: retrieve relevant chunks, then generate an answer."""
    model_name = "llama-3.3-70b-versatile"

    results = search_chunks(db, request.question, request.top_k)

    if not results:
        return QuestionAnswer(
            answer="No documents found in the knowledge base. Please upload documents first.",
            model_used=model_name
        )

    context_parts = []
    for i, result in enumerate(results):
        context_parts.append(f"[Source {i+1}]: {result['content']}")

    context_text = "\n\n".join(context_parts)

    prompt = f"""Answer the following question using ONLY the context provided below.
If the context does not contain enough information to answer the question, say so.

Do NOT use any knowledge outside of the provided context.

CONTEXT:
{context_text}

QUESTION: {request.question}

ANSWER:"""

    try:
        answer = test_agent(
            llm_id=model_name,
            query=[prompt],
            allow_search=False,
            system_prompt="You are a knowledge base assistant. Answer questions using the provided document context.",
            provider="groq"
        )

        return QuestionAnswer(
            answer=answer,
            model_used=model_name
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": f"Answer generation failed: {str(e)}", "error_code": "ANSWER_ERROR"}
        )
