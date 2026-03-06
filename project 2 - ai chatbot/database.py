

import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


# ============================================================
# Database Connection Setup
# ============================================================

# PostgreSQL connection URL from .env file
# Format: postgresql://username:password@host:port/database_name
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgresql:1234@localhost:5432/deepak"
)

# create_engine: Creates the connection pool to PostgreSQL
# pool_size=5: Keep 5 connections open (reused across requests)
# max_overflow=10: Allow up to 10 extra connections during high traffic
engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10
)

# sessionmaker: Creates a factory for database sessions
# autocommit=False: We control when data is saved (safer)
# autoflush=False: We control when data is sent to the database
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base: All database models inherit from this
Base = declarative_base()


# ============================================================
# AuditLog Table Model
# ============================================================

class AuditLog(Base):
    """
    Records EVERY tool call made to the system.
    
    Each row answers these questions:
    - WHO called the tool? (user_id, ip_address)
    - WHAT tool was called? (tool_name)
    - WHAT did they send? (input_data)
    - WHAT did they get back? (output_data)
    - WHEN did it happen? (timestamp)
    - DID it work? (status: 'success' or 'error')
    - WHY did it fail? (error_message)
    
    This is like a security camera for your API.
    """
    __tablename__ = "audit_logs"  # Name of the table in SQLite

    # Primary key — auto-incrementing unique ID for each log entry
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # WHO: User identification
    user_id = Column(String(100), nullable=True, default="anonymous")  # Who called it
    ip_address = Column(String(45), nullable=True)                      # Their IP address
    
    # WHAT: Tool information
    tool_name = Column(String(50), nullable=False)    # e.g. "summarize" or "extract_json"
    input_data = Column(Text, nullable=True)           # What the user sent (JSON string)
    output_data = Column(Text, nullable=True)          # What we returned (JSON string)
    
    # STATUS: Did it work?
    status = Column(String(20), nullable=False, default="started")  # "started", "success", "error"
    error_message = Column(Text, nullable=True)        # Error details if it failed
    
    # WHEN: Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow)  # When the call happened


# ============================================================
# Create the table in the database
# ============================================================

# This line creates the audit_logs table if it doesn't exist yet
# It's safe to call multiple times — it won't delete existing data
Base.metadata.create_all(bind=engine)


# ============================================================
# Helper Functions
# ============================================================

def get_db():
    """
    FastAPI Dependency: Provides a database session.
    
    Usage in an endpoint:
        @app.post("/tools/summarize")
        async def summarize(db: Session = Depends(get_db)):
            # Use db to read/write audit logs
            
    The 'yield' keyword means:
    1. Create a database session
    2. Give it to the endpoint (yield)
    3. After the endpoint finishes, close the session (finally block)
    
    This prevents database connection leaks.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def log_tool_call(
    db: Session,
    tool_name: str,
    input_data: str,
    output_data: str = None,
    status: str = "success",
    error_message: str = None,
    user_id: str = "anonymous",
    ip_address: str = None
) -> AuditLog:
    """
    Helper function to create an audit log entry.
    
    This is called inside every tool endpoint:
    - On SUCCESS: log_tool_call(db, "summarize", input_text, summary, "success")
    - On ERROR: log_tool_call(db, "summarize", input_text, None, "error", str(e))
    
    Parameters:
        db: Database session (from get_db dependency)
        tool_name: Name of the tool ("summarize" or "extract_json")
        input_data: What the user sent (as a string)
        output_data: What we returned (as a string)
        status: "success" or "error"
        error_message: Error details if status is "error"
        user_id: Who called it (from API key or "anonymous")
        ip_address: Caller's IP address
    
    Returns:
        The created AuditLog entry
    """
    # Create a new audit log entry
    log_entry = AuditLog(
        tool_name=tool_name,
        input_data=input_data,
        output_data=output_data,
        status=status,
        error_message=error_message,
        user_id=user_id,
        ip_address=ip_address,
        timestamp=datetime.utcnow()
    )
    
    # Save to database
    db.add(log_entry)     # Add the entry to the session
    db.commit()           # Write it to the database file
    db.refresh(log_entry) # Reload from DB to get the auto-generated ID
    
    return log_entry
