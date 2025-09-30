"""
Enhanced middleware for authentication, logging, and request processing.

CRITICAL: Request processing pipeline - affects all API calls
SECURITY: Authentication and authorization enforcement
"""

from fastapi import Request, Response, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, Dict, Any, Optional
import time
import jwt
from datetime import datetime
import logging

from utils.logging_config import setup_logging

logger = setup_logging(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Enhanced authentication middleware with session management.
    
    SECURITY: JWT validation and session tracking
    FALLBACK: Graceful handling of authentication failures
    """
    
    def __init__(self, app, jwt_secret: str, jwt_algorithm: str = "HS256"):
        super().__init__(app)
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = jwt_algorithm
        
        # Public endpoints that don't require authentication
        self.public_endpoints = {
            "/",
            "/health",
            "/api/v1/auth/login",
            "/docs",
            "/openapi.json",
            "/redoc"
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with authentication checks."""
        
        # Skip authentication for public endpoints
        if request.url.path in self.public_endpoints:
            return await call_next(request)
        
        # Skip authentication for static files
        if request.url.path.startswith("/static"):
            return await call_next(request)
        
        # Extract and validate JWT token
        try:
            auth_header = request.headers.get("Authorization")
            
            if not auth_header or not auth_header.startswith("Bearer "):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing or invalid authorization header",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            token = auth_header.split(" ")[1]
            
            # Validate JWT token
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            
            # Add user info to request state
            request.state.user = {
                "user_id": payload.get("sub"),
                "username": payload.get("username"),
                "permissions": payload.get("permissions", []),
                "authenticated_at": payload.get("iat")
            }
            
            # Log successful authentication
            logger.debug("Request authenticated", 
                        user=request.state.user["username"],
                        path=request.url.path)
            
        except jwt.ExpiredSignatureError:
            logger.warning("Expired token used", path=request.url.path)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except jwt.JWTError as e:
            logger.warning("Invalid token used", path=request.url.path, error=str(e))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Authentication middleware error", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service error"
            )
        
        # Process request
        response = await call_next(request)
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Request logging and performance monitoring middleware.
    
    CRITICAL: Request tracking and performance monitoring
    """
    
    def __init__(self, app, database_manager=None):
        super().__init__(app)
        self.database_manager = database_manager
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request details and performance metrics."""
        
        start_time = time.time()
        
        # Extract request info
        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Get user info if authenticated
        user_id = getattr(request.state, "user", {}).get("user_id", "anonymous")
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate response time
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Log request
            logger.info("API request processed",
                       method=method,
                       path=path,
                       status_code=response.status_code,
                       response_time_ms=response_time_ms,
                       user_id=user_id,
                       client_ip=client_ip)
            
            # Store performance metrics in database
            if self.database_manager:
                try:
                    await self._store_performance_metric(
                        path, method, response_time_ms, 
                        response.status_code, user_id
                    )
                except Exception as e:
                    logger.error("Failed to store performance metric", error=str(e))
            
            # Add performance headers
            response.headers["X-Response-Time"] = f"{response_time_ms}ms"
            response.headers["X-Request-ID"] = f"{int(start_time * 1000)}"
            
            return response
            
        except Exception as e:
            # Log error
            response_time_ms = int((time.time() - start_time) * 1000)
            
            logger.error("API request failed",
                        method=method,
                        path=path,
                        response_time_ms=response_time_ms,
                        user_id=user_id,
                        client_ip=client_ip,
                        error=str(e))
            
            raise
    
    async def _store_performance_metric(self, endpoint: str, method: str, 
                                      response_time_ms: int, status_code: int, 
                                      user_id: str):
        """Store performance metric in database."""
        try:
            await self.database_manager.execute_update(
                "analytics",
                """
                INSERT INTO performance_metrics 
                (endpoint, method, response_time_ms, status_code, user_id, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (endpoint, method, response_time_ms, status_code, user_id, 
                 datetime.utcnow().isoformat())
            )
        except Exception as e:
            logger.error("Failed to store performance metric", error=str(e))


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware to prevent abuse.
    
    SECURITY: API abuse prevention
    COST: Prevent excessive resource usage
    """
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts: Dict[str, Dict[str, Any]] = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting based on client IP and user."""
        
        # Get client identifier
        client_ip = request.client.host if request.client else "unknown"
        user_id = getattr(request.state, "user", {}).get("user_id", "anonymous")
        client_key = f"{client_ip}:{user_id}"
        
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/api/v1/system/health"]:
            return await call_next(request)
        
        current_time = time.time()
        current_minute = int(current_time // 60)
        
        # Initialize or update request count
        if client_key not in self.request_counts:
            self.request_counts[client_key] = {
                "minute": current_minute,
                "count": 0
            }
        
        client_data = self.request_counts[client_key]
        
        # Reset count if new minute
        if client_data["minute"] != current_minute:
            client_data["minute"] = current_minute
            client_data["count"] = 0
        
        # Check rate limit
        if client_data["count"] >= self.requests_per_minute:
            logger.warning("Rate limit exceeded", 
                          client_key=client_key,
                          path=request.url.path,
                          count=client_data["count"])
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {self.requests_per_minute} requests per minute.",
                headers={"Retry-After": "60"}
            )
        
        # Increment request count
        client_data["count"] += 1
        
        # Clean up old entries periodically
        if len(self.request_counts) > 1000:
            self._cleanup_old_entries(current_minute)
        
        return await call_next(request)
    
    def _cleanup_old_entries(self, current_minute: int):
        """Remove old rate limiting entries."""
        keys_to_remove = [
            key for key, data in self.request_counts.items()
            if current_minute - data["minute"] > 5  # Keep last 5 minutes
        ]
        
        for key in keys_to_remove:
            del self.request_counts[key]


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Global error handling middleware.
    
    FALLBACK: Graceful error responses
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle uncaught exceptions gracefully."""
        
        try:
            return await call_next(request)
            
        except HTTPException:
            # Re-raise HTTP exceptions (they're handled by FastAPI)
            raise
            
        except Exception as e:
            # Log unexpected errors
            logger.error("Unhandled exception in request",
                        method=request.method,
                        path=request.url.path,
                        error=str(e),
                        error_type=type(e).__name__)
            
            # Return generic error response
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred. Please try again later."
            )