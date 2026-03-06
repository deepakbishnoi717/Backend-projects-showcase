import os
import json
import math
import re
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session

from kb_models import KBDocument, KBChunk, KBEmbedding
from validators import make_filename_safe, sanitize_text_input


# Configuration
ALLOWED_FILE_TYPES = {"txt", "pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
UPLOAD_DIR = "uploads"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
EMBEDDING_DIMENSIONS = 384


def validate_file(filename: str, file_size: int) -> Tuple[bool, str]:
    """Validates file type and size. Returns (is_valid, message)."""
    if not filename:
        return False, "Filename is required"

    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if extension not in ALLOWED_FILE_TYPES:
        return False, f"File type '.{extension}' not allowed. Allowed types: {', '.join(ALLOWED_FILE_TYPES)}"

    if file_size > MAX_FILE_SIZE:
        max_mb = MAX_FILE_SIZE / (1024 * 1024)
        actual_mb = file_size / (1024 * 1024)
        return False, f"File too large ({actual_mb:.1f} MB). Maximum is {max_mb:.0f} MB"

    if file_size == 0:
        return False, "File is empty (0 bytes)"

    return True, "ok"


def save_uploaded_file(filename: str, content: bytes) -> str:
    """Saves uploaded file to disk with a safe filename. Returns file path."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    safe_name = make_filename_safe(filename)

    file_path = os.path.join(UPLOAD_DIR, safe_name)
    counter = 1
    base_name, ext = os.path.splitext(safe_name)
    while os.path.exists(file_path):
        file_path = os.path.join(UPLOAD_DIR, f"{base_name}_{counter}{ext}")
        counter += 1

    with open(file_path, "wb") as f:
        f.write(content)

    return file_path


def extract_text_from_file(file_path: str, file_type: str) -> str:
    """Extracts plain text from a .txt or .pdf file."""
    if file_type == "txt":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    elif file_type == "pdf":
        try:
            import PyPDF2
            text_parts = []
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            return "\n\n".join(text_parts)
        except ImportError:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

    else:
        raise ValueError(f"Unsupported file type: {file_type}")


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[dict]:
    """Splits text into overlapping chunks. Returns list of chunk dicts."""
    if not text or not text.strip():
        return []

    text = sanitize_text_input(text, max_length=1000000)

    chunks = []
    start = 0
    chunk_index = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk_content = text[start:end].strip()

        if chunk_content:
            chunks.append({
                "content": chunk_content,
                "char_start": start,
                "char_end": end,
                "chunk_index": chunk_index
            })
            chunk_index += 1

        start += chunk_size - overlap

        if chunk_size - overlap <= 0:
            break

    return chunks


def store_chunks(db: Session, document_id: int, chunks: List[dict]) -> int:
    """Saves text chunks to the database. Returns number of chunks stored."""
    for chunk_data in chunks:
        chunk = KBChunk(
            document_id=document_id,
            chunk_index=chunk_data["chunk_index"],
            content=chunk_data["content"],
            char_start=chunk_data["char_start"],
            char_end=chunk_data["char_end"]
        )
        db.add(chunk)

    db.commit()
    return len(chunks)


def generate_embedding(text: str) -> List[float]:
    """Generates a vector embedding for text using sentence-transformers (with hash fallback)."""
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        embedding = model.encode(text).tolist()
        return embedding
    except ImportError:
        import hashlib
        hash_bytes = hashlib.sha384(text.encode()).digest()
        embedding = [(byte / 128.0) - 1.0 for byte in hash_bytes]
        while len(embedding) < EMBEDDING_DIMENSIONS:
            embedding.append(0.0)
        return embedding[:EMBEDDING_DIMENSIONS]


def store_embedding(db: Session, chunk_id: int, embedding: List[float]) -> KBEmbedding:
    """Stores a vector embedding in the database as JSON."""
    emb_record = KBEmbedding(
        chunk_id=chunk_id,
        embedding_data=json.dumps(embedding),
        embedding_model="all-MiniLM-L6-v2",
        dimensions=len(embedding)
    )

    db.add(emb_record)
    db.commit()
    db.refresh(emb_record)
    return emb_record


def process_document_embeddings(db: Session, document_id: int) -> int:
    """Generates and stores embeddings for all chunks of a document."""
    chunks = db.query(KBChunk).filter(KBChunk.document_id == document_id).all()

    count = 0
    for chunk in chunks:
        if chunk.embedding is not None:
            continue
        embedding = generate_embedding(chunk.content)
        store_embedding(db, chunk.id, embedding)
        count += 1

    return count


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Calculates cosine similarity between two vectors. Returns float in [-1, 1]."""
    if len(vec_a) != len(vec_b):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    magnitude_a = math.sqrt(sum(a * a for a in vec_a))
    magnitude_b = math.sqrt(sum(b * b for b in vec_b))

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)


def search_chunks(db: Session, query: str, top_k: int = 5) -> List[dict]:
    """Searches the knowledge base for chunks most relevant to the query."""
    query_embedding = generate_embedding(query)
    all_embeddings = db.query(KBEmbedding).all()

    if not all_embeddings:
        return []

    results = []
    for emb_record in all_embeddings:
        stored_embedding = json.loads(emb_record.embedding_data)
        score = cosine_similarity(query_embedding, stored_embedding)
        normalized_score = (score + 1) / 2

        chunk = db.query(KBChunk).filter(KBChunk.id == emb_record.chunk_id).first()
        if chunk:
            document = db.query(KBDocument).filter(KBDocument.id == chunk.document_id).first()
            results.append({
                "chunk_id": chunk.id,
                "score": round(normalized_score, 4),
                "content": chunk.content,
                "source": {
                    "document_id": chunk.document_id,
                    "filename": document.filename if document else "unknown",
                    "chunk_index": chunk.chunk_index
                }
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]

