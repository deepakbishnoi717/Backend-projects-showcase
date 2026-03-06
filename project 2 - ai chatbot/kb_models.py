from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, LargeBinary, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from database import Base, engine


class KBDocument(Base):
    """Uploaded file metadata."""
    __tablename__ = "kb_documents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    safe_filename = Column(String(255), nullable=False)
    file_type = Column(String(10), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_path = Column(String(500), nullable=False)
    status = Column(String(20), default="uploaded")
    chunk_count = Column(Integer, default=0)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    chunks = relationship("KBChunk", back_populates="document", cascade="all, delete-orphan")


class KBChunk(Base):
    """Text chunk from a document."""
    __tablename__ = "kb_chunks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("kb_documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    char_start = Column(Integer, default=0)
    char_end = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("KBDocument", back_populates="chunks")
    embedding = relationship("KBEmbedding", back_populates="chunk", uselist=False, cascade="all, delete-orphan")


class KBEmbedding(Base):
    """Vector embedding for a chunk."""
    __tablename__ = "kb_embeddings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    chunk_id = Column(Integer, ForeignKey("kb_chunks.id"), nullable=False, unique=True)
    embedding_data = Column(Text, nullable=False)
    embedding_model = Column(String(100), default="all-MiniLM-L6-v2")
    dimensions = Column(Integer, default=384)
    created_at = Column(DateTime, default=datetime.utcnow)

    chunk = relationship("KBChunk", back_populates="embedding")


Base.metadata.create_all(bind=engine)



