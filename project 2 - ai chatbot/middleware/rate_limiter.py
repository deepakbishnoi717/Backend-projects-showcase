"""
Day 17 — Rate Limiting Upgrade: Per-Route Limits + Cooldown
=============================================================
This middleware controls HOW MANY requests each user (IP address) can make.

What changed from the old version?
- OLD: Same limit for all routes (10 requests/minute for everything)
- NEW: Different limits for different routes:
    - /tools/* routes: 5 requests/minute (strict — these are expensive AI calls)
    - /chat route: 10 requests/minute (moderate)
    - Other routes: 30 requests/minute (relaxed — health checks, etc.)

NEW: Cooldown mechanism
- If a user fails 5 times in a row (errors, bad input, etc.), they get BLOCKED for 5 minutes
- This prevents brute-force attacks and abuse

How rate limiting works (Sliding Window algorithm):
1. We store timestamps of each request per IP address
2. When a new request comes in, we count how many happened in the last 60 seconds
3. If it exceeds the limit → block the request with HTTP 429 (Too Many Requests)
"""

import time
from collections import defaultdict
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import config


# ============================================================
# Per-Route Rate Limit Configuration
# ============================================================

# Different routes get different limits
# Why? Tool endpoints use expensive AI calls, so they need stricter limits
ROUTE_LIMITS = {
    "tools": {
        "requests": 5,       # Only 5 tool calls per window
        "window": 60,        # Per 60 seconds
    },
    "chat": {
        "requests": config.RATE_LIMIT_REQUESTS,  # 10 per window (from .env)
        "window": config.RATE_LIMIT_WINDOW,       # 60 seconds (from .env)
    },
    "default": {
        "requests": 30,      # 30 requests per window for other routes
        "window": 60,
    }
}

# Cooldown configuration
COOLDOWN_FAILURE_THRESHOLD = 5    # After 5 consecutive failures...
COOLDOWN_DURATION = 300           # ...block the IP for 5 minutes (300 seconds)


class RateLimiter:
    """
    In-memory rate limiter using sliding window algorithm.
    
    Sliding window means:
    - We look at the LAST 60 seconds (not fixed 1-minute blocks)
    - This prevents the "double burst" problem at minute boundaries
    
    Example:
    - At 12:00:59 user sends 10 requests (allowed)
    - At 12:01:01 user sends 10 more (in a fixed window, this would be allowed!)
    - With sliding window, we see 20 requests in 62 seconds → BLOCKED
    """
    
    def __init__(self):
        # Tracks request timestamps per IP per route type
        # Structure: {"192.168.1.1": {"tools": [timestamp1, timestamp2, ...], "chat": [...]}}
        self.requests = defaultdict(lambda: defaultdict(list))
        
        # Tracks consecutive failures per IP
        # Structure: {"192.168.1.1": {"count": 3, "last_failure": timestamp}}
        self.failures = defaultdict(lambda: {"count": 0, "last_failure": 0})
        
        # Tracks IPs in cooldown
        # Structure: {"192.168.1.1": cooldown_end_timestamp}
        self.cooldowns = {}
    
    def _get_route_type(self, path: str) -> str:
        """
        Determines which rate limit category a URL path belongs to.
        
        Why per-route?
        - /tools/summarize uses expensive AI calls → strict limit (5/min)
        - /chat is the main feature → moderate limit (10/min)
        - / (health check) is cheap → relaxed limit (30/min)
        
        Examples:
            "/tools/summarize"  → "tools"  (5 requests/minute)
            "/tools/extract_json" → "tools"
            "/chat"             → "chat"   (10 requests/minute)
            "/"                 → "default" (30 requests/minute)
        """
        if path.startswith("/tools"):
            return "tools"
        elif path.startswith("/kb"):
            return "tools"  # KB routes get same strict limits as tools
        elif path in ["/chat", "/ai/chat/stream"]:
            return "chat"
        else:
            return "default"
    
    def is_in_cooldown(self, ip: str) -> bool:
        """
        Checks if an IP address is currently in the cooldown period.
        
        Cooldown happens when a user makes too many consecutive failed requests.
        This prevents brute-force attacks and abuse.
        
        Example:
            User sends 5 bad requests → 5-minute cooldown activated
            During cooldown → ALL requests are blocked (returns True)
            After 5 minutes → cooldown expires (returns False)
        """
        if ip in self.cooldowns:
            if time.time() < self.cooldowns[ip]:
                return True  # Still in cooldown period
            else:
                # Cooldown expired — remove it and reset failure count
                del self.cooldowns[ip]
                self.failures[ip] = {"count": 0, "last_failure": 0}
        return False
    
    def record_failure(self, ip: str):
        """
        Records a failed request from an IP address.
        
        After COOLDOWN_FAILURE_THRESHOLD (5) consecutive failures,
        the IP gets blocked for COOLDOWN_DURATION (5 minutes).
        
        Why track failures?
        - Someone trying random API keys → gets blocked after 5 attempts
        - Someone sending garbage data → gets blocked after 5 attempts
        - Bot spamming with invalid requests → gets blocked
        
        The counter resets on success (record_success method).
        """
        self.failures[ip]["count"] += 1
        self.failures[ip]["last_failure"] = time.time()
        
        # Check if threshold exceeded
        if self.failures[ip]["count"] >= COOLDOWN_FAILURE_THRESHOLD:
            # Activate cooldown — block for 5 minutes
            self.cooldowns[ip] = time.time() + COOLDOWN_DURATION
    
    def record_success(self, ip: str):
        """
        Records a successful request — resets the failure counter.
        
        Why reset on success?
        - If a user has 4 failures then 1 success, they're probably legitimate
        - We don't want to punish users who make occasional mistakes
        - Only CONSECUTIVE failures trigger cooldown
        """
        self.failures[ip] = {"count": 0, "last_failure": 0}

    def is_allowed(self, ip: str, path: str) -> bool:
        """
        Main method: checks if a request from this IP to this path is allowed.
        
        Steps:
        1. Check if IP is in cooldown → block immediately
        2. Determine the route type (tools/chat/default)
        3. Get the limit for that route type
        4. Count requests in the sliding window
        5. If under limit → allow (return True)
        6. If over limit → block (return False)
        """
        now = time.time()
        route_type = self._get_route_type(path)
        limits = ROUTE_LIMITS[route_type]
        
        window_start = now - limits["window"]
        
        # Clean old requests outside the window
        # This removes timestamps older than 60 seconds
        self.requests[ip][route_type] = [
            timestamp for timestamp in self.requests[ip][route_type]
            if timestamp > window_start
        ]
        
        # Check if this request would exceed the limit
        if len(self.requests[ip][route_type]) >= limits["requests"]:
            return False  # Rate limit exceeded!
        
        # Allow the request and record the timestamp
        self.requests[ip][route_type].append(now)
        return True
    
    def get_retry_after(self, ip: str, path: str) -> int:
        """
        Returns how many seconds the user should wait before trying again.
        
        This is sent in the HTTP response header 'Retry-After'
        so the client knows when to retry.
        """
        # If in cooldown, return remaining cooldown time
        if ip in self.cooldowns:
            return int(self.cooldowns[ip] - time.time())
        
        route_type = self._get_route_type(path)
        
        if not self.requests[ip][route_type]:
            return 0
        
        oldest = min(self.requests[ip][route_type])
        limits = ROUTE_LIMITS[route_type]
        return int(limits["window"] - (time.time() - oldest))
    
    def get_limit_for_path(self, path: str) -> dict:
        """Returns the rate limit config for a given path (used in error responses)."""
        route_type = self._get_route_type(path)
        return ROUTE_LIMITS[route_type]


# Global rate limiter instance (shared across all requests)
rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI Middleware: Runs BEFORE every request reaches your endpoint.
    
    Flow:
    1. Request comes in → middleware checks rate limit
    2. If allowed → pass to endpoint (call_next)
    3. If blocked → return 429 error immediately (endpoint never runs)
    4. After endpoint → record success or failure for cooldown tracking
    
    Middleware is like a security guard at the entrance:
    - Checks your ID (IP address)
    - Counts how many times you've entered (request count)
    - Turns you away if you've been too many times (rate limit)
    - Remembers if you caused problems (failure tracking)
    """
    
    async def dispatch(self, request: Request, call_next):
        # Only rate-limit AI-related endpoints
        # We don't want to rate-limit docs, health checks, etc.
        path = request.url.path
        
        if path.startswith("/tools") or path.startswith("/kb") or path in ["/chat", "/ai/chat/stream"]:
            client_ip = request.client.host
            
            # Step 1: Check cooldown first
            if rate_limiter.is_in_cooldown(client_ip):
                retry_after = rate_limiter.get_retry_after(client_ip, path)
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Too many failed attempts. You are in a cooldown period.",
                        "error_code": "COOLDOWN_ACTIVE",
                        "details": {
                            "retry_after": retry_after,
                            "message": "Please wait before trying again."
                        }
                    },
                    headers={"Retry-After": str(retry_after)}
                )
            
            # Step 2: Check per-route rate limit
            if not rate_limiter.is_allowed(client_ip, path):
                retry_after = rate_limiter.get_retry_after(client_ip, path)
                limits = rate_limiter.get_limit_for_path(path)
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Too many requests",
                        "error_code": "RATE_LIMIT_EXCEEDED",
                        "details": {
                            "retry_after": retry_after,
                            "limit": limits["requests"],
                            "window": limits["window"],
                            "route": path
                        }
                    },
                    headers={"Retry-After": str(retry_after)}
                )
        
        # Step 3: Process the request
        try:
            response = await call_next(request)
            
            # Step 4: Record success or failure based on status code
            if path.startswith("/tools") or path.startswith("/kb") or path in ["/chat", "/ai/chat/stream"]:
                client_ip = request.client.host
                if response.status_code >= 400:
                    # 4xx or 5xx = failure
                    rate_limiter.record_failure(client_ip)
                else:
                    # 2xx or 3xx = success
                    rate_limiter.record_success(client_ip)
            
            return response
            
        except HTTPException:
            # Re-raise HTTP exceptions (like our 429 above)
            raise
        except Exception:
            # Record failure for unexpected errors
            if path.startswith("/tools") or path.startswith("/kb") or path in ["/chat", "/ai/chat/stream"]:
                client_ip = request.client.host
                rate_limiter.record_failure(client_ip)
            raise
