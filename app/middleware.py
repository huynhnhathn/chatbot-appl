from fastapi import Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Set
import time
import json
import hashlib
from datetime import datetime, timedelta
from app.logger import get_logger
from config import settings

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware for API endpoints."""
    
    def __init__(self, app):
        super().__init__(app)
        self.requests_per_minute: Dict[str, list] = {}
        self.requests_per_hour: Dict[str, list] = {}
    
    async def dispatch(self, request: Request, call_next):
        # Get client identifier (IP address or user ID)
        client_id = self._get_client_id(request)
        
        # Check rate limits
        if not self._check_rate_limit(client_id):
            logger.warning("Rate limit exceeded", client_id=client_id, path=request.url.path)
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later."
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit-Minute"] = str(settings.rate_limit_per_minute)
        response.headers["X-RateLimit-Limit-Hour"] = str(settings.rate_limit_per_hour)
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier."""
        # Try to get user ID from headers or query params
        user_id = request.headers.get("X-User-ID") or request.query_params.get("user_id")
        if user_id:
            return f"user_{user_id}"
        
        # Fall back to IP address
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return f"ip_{forwarded_for.split(',')[0].strip()}"
        
        return f"ip_{request.client.host}"
    
    def _check_rate_limit(self, client_id: str) -> bool:
        """Check if client has exceeded rate limits."""
        now = datetime.utcnow()
        
        # Clean old entries
        self._clean_old_entries(client_id, now)
        
        # Check minute limit
        minute_requests = self.requests_per_minute.get(client_id, [])
        if len(minute_requests) >= settings.rate_limit_per_minute:
            return False
        
        # Check hour limit
        hour_requests = self.requests_per_hour.get(client_id, [])
        if len(hour_requests) >= settings.rate_limit_per_hour:
            return False
        
        # Add current request
        minute_requests.append(now)
        hour_requests.append(now)
        
        self.requests_per_minute[client_id] = minute_requests
        self.requests_per_hour[client_id] = hour_requests
        
        return True
    
    def _clean_old_entries(self, client_id: str, now: datetime) -> None:
        """Remove old rate limit entries."""
        # Clean minute entries
        minute_requests = self.requests_per_minute.get(client_id, [])
        minute_requests = [req for req in minute_requests if now - req < timedelta(minutes=1)]
        self.requests_per_minute[client_id] = minute_requests
        
        # Clean hour entries
        hour_requests = self.requests_per_hour.get(client_id, [])
        hour_requests = [req for req in hour_requests if now - req < timedelta(hours=1)]
        self.requests_per_hour[client_id] = hour_requests


class LoggingMiddleware(BaseHTTPMiddleware):
    """Request/response logging middleware."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log request
        request_id = self._generate_request_id()
        logger.info(
            "Incoming request",
            request_id=request_id,
            method=request.method,
            url=str(request.url),
            client_ip=request.client.host,
            user_agent=request.headers.get("user-agent", "")
        )
        
        # Process request
        try:
            response = await call_next(request)
            response_time = time.time() - start_time
            
            # Log successful response
            logger.info(
                "Request completed",
                request_id=request_id,
                status_code=response.status_code,
                response_time=round(response_time, 3)
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            response_time = time.time() - start_time
            
            # Log error
            logger.error(
                "Request failed",
                request_id=request_id,
                error=str(e),
                response_time=round(response_time, 3)
            )
            raise


class SecurityMiddleware(BaseHTTPMiddleware):
    """Security middleware for additional headers and checks."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        return response
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        return hashlib.md5(f"{time.time()}".encode()).hexdigest()[:8]


def setup_middleware(app):
    """Setup all middleware for the FastAPI application."""
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # Trusted host middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # Configure based on your domain in production
    )
    
    # Custom middleware
    app.add_middleware(SecurityMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RateLimitMiddleware)
    
    logger.info("Middleware setup completed")