"""
Day 18 — Security Checklist: Configuration Settings
======================================================
Centralized configuration for ALL settings in the AI Agent.

SECURITY RULES:
1. ALL secrets (API keys, passwords) come from .env file
2. NEVER hardcode secrets in code files
3. .env is in .gitignore so it's NEVER pushed to GitHub
4. Different settings for development vs production (CORS)

What is python-dotenv?
- Reads the .env file and loads values into os.environ
- os.getenv("KEY") reads the value
- os.getenv("KEY", "default") provides a fallback if KEY is not in .env
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
# This MUST be called before any os.getenv() calls
load_dotenv()


# ============================================================
# API Keys — ALL from environment variables (NEVER hardcoded!)
# ============================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Tool Authentication Key — required to access /tools/* endpoints
# Users must send this in the X-API-Key header
# If not set in .env, we generate a default for development only
TOOL_API_KEY = os.getenv("TOOL_API_KEY", "dev-tool-key-change-in-production")


# ============================================================
# AI Configuration
# ============================================================

AI_TIMEOUT = int(os.getenv("AI_TIMEOUT", "30"))         # Max seconds to wait for AI response
AI_MAX_RETRIES = int(os.getenv("AI_MAX_RETRIES", "3"))   # Retry count on failure
AI_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "2000"))  # Max tokens in AI response


# ============================================================
# Rate Limiting
# ============================================================

RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "10"))  # Requests per window
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))      # Window in seconds


# ============================================================
# CORS (Cross-Origin Resource Sharing) Settings
# ============================================================
# 
# What is CORS?
# - Browsers block requests from one domain to another by default
# - Example: your frontend at localhost:3000 calling your API at localhost:8000
# - You must explicitly allow which domains can call your API
#
# Why not allow all origins ("*")?
# - In production, if you allow "*", ANY website in the world can call your API
# - Someone could create a malicious website that uses YOUR AI agent for free
# - Always restrict to only YOUR frontend domain(s)

# Environment: "development" or "production"
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Allowed origins — which frontend URLs can call this API
# DEVELOPMENT: Allow localhost (for testing)
# PRODUCTION: Only allow your real domain
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"
).split(",")
# ^ split(",") converts "http://localhost:3000,http://localhost:5173"
#   into ["http://localhost:3000", "http://localhost:5173"]


# ============================================================
# Logging
# ============================================================

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "json"  # json or text
