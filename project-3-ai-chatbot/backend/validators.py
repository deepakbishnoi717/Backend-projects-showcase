"""
Day 16 — Validation Hardening: Input Sanitization Helpers
==========================================================
This file contains utility functions that clean user input
to prevent security issues and crashes.

Why do we need this?
- Users can send ANYTHING: SQL injection, script tags, weird characters
- Filenames like "../../etc/passwd" can access system files
- Super long strings can crash your server or waste memory
- These helpers make any user input SAFE before processing it
"""

import re
from typing import Optional


def make_filename_safe(name: str) -> str:
    """
    Converts ANY user string into a safe filename.
    
    Why?
    - Users might send filenames like: ../../etc/passwd (directory traversal attack)
    - Or filenames with special chars: my file!@#$.txt (causes OS errors)
    - Or filenames that are too long (some systems limit to 255 chars)
    
    What this does:
    1. Remove path separators (/ and \\) — prevents directory traversal
    2. Replace special characters with underscores
    3. Remove leading dots (hidden files on Linux, security risk)
    4. Limit length to 100 characters
    5. Provide a default if the result is empty
    
    Examples:
        make_filename_safe("../../etc/passwd")     → "etc_passwd"
        make_filename_safe("my file!@#.txt")       → "my_file___.txt"
        make_filename_safe("   ...hidden   ")      → "hidden"
        make_filename_safe("")                      → "unnamed"
    """
    if not name or not name.strip():
        return "unnamed"
    
    # Step 1: Remove path separators to prevent directory traversal
    # "../../etc/passwd" → "....etc.passwd"
    safe = name.replace("/", "_").replace("\\", "_")
    
    # Step 2: Replace any character that's NOT a letter, number, underscore, hyphen, or dot
    # "my file!@#.txt" → "my_file___.txt"
    safe = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', safe)
    
    # Step 3: Remove leading/trailing dots and whitespace
    # "...hidden..." → "hidden"
    safe = safe.strip('.').strip('_').strip()
    
    # Step 4: Collapse multiple underscores into one
    # "my___file" → "my_file"
    safe = re.sub(r'_+', '_', safe)
    
    # Step 5: Limit length to 100 characters
    safe = safe[:100]
    
    # Step 6: If everything was removed, use a default name
    if not safe:
        return "unnamed"
    
    return safe


def sanitize_text_input(text: str, max_length: int = 10000) -> str:
    """
    Cleans text input by removing potentially dangerous content.
    
    Why?
    - Users might embed HTML/script tags: <script>alert('hacked')</script>
    - Null bytes can cause issues in C-based systems: "hello\\x00world"
    - Control characters can break logging and display
    
    What this does:
    1. Remove null bytes (\\x00) — these can bypass security checks
    2. Remove control characters (except newlines and tabs, which are normal)
    3. Trim to max_length — prevents memory abuse
    4. Strip leading/trailing whitespace
    
    Examples:
        sanitize_text_input("hello\\x00world")  → "helloworld"
        sanitize_text_input("<script>bad</script>")  → "<script>bad</script>" (kept but harmless in API)
    """
    if not text:
        return ""
    
    # Step 1: Remove null bytes — these are NEVER valid in user text
    text = text.replace('\x00', '')
    
    # Step 2: Remove control characters except \\n (newline) and \\t (tab)
    # Control chars are ASCII 0-31, we keep 9 (tab) and 10 (newline)
    text = re.sub(r'[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    
    # Step 3: Trim to maximum length
    text = text[:max_length]
    
    # Step 4: Strip whitespace from ends
    text = text.strip()
    
    return text


def validate_model_name(model_name: str) -> bool:
    """
    Checks if a model name is valid.
    
    Valid model names only contain:
    - Letters (a-z, A-Z)
    - Numbers (0-9)
    - Hyphens (-) and dots (.)
    
    Why?
    - Prevents injection attacks through model name field
    - Model names like "gpt-4o-mini" or "llama-3.3-70b-versatile" are valid
    - Model names like "'; DROP TABLE users;--" are NOT valid
    
    Examples:
        validate_model_name("gpt-4o-mini")              → True
        validate_model_name("llama-3.3-70b-versatile")   → True
        validate_model_name("bad model!@#$")              → False
    """
    # Only allow alphanumeric, hyphens, and dots
    pattern = r'^[a-zA-Z0-9\-\.]+$'
    return bool(re.match(pattern, model_name))
