"""
Authentication and authorization API endpoints.

SECURITY: JWT-based authentication with session management
FALLBACK: Basic authentication if advanced features fail
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, Dict, Any
import jwt
from datetime import datetime, timedelta
import secrets

from ...utils.logging_config import setup_logging

logger = setup_logging(__name__)

router = APIRouter()
security = HTTPBearer()

# SECURITY: JWT configuration
JWT_SECRET_KEY = secrets.token_urlsafe(32)  # In production, use environment variable
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class UserInfo(BaseModel):
    user_id: str
    username: str
    permissions: list[str]


# Temporary user store (in production, use proper user management)
TEMP_USERS = {
    "admin": {
        "password": "admin123",  # In production, use hashed passwords
        "permissions": ["read", "write", "admin"]
    },
    "user": {
        "password": "user123",
        "permissions": ["read"]
    }
}


def create_access_token(data: Dict[str, Any]) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Verify JWT token and return user data.
    
    SECURITY: Validate token signature and expiration
    """
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/login", response_model=TokenResponse)
async def login(login_request: LoginRequest):
    """
    Authenticate user and return JWT token.
    
    SECURITY: Validate credentials against user store
    """
    username = login_request.username
    password = login_request.password
    
    # SECURITY: Validate user credentials
    if username not in TEMP_USERS or TEMP_USERS[username]["password"] != password:
        logger.warning("Failed login attempt", username=username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Create token payload
    token_data = {
        "sub": username,
        "username": username,
        "permissions": TEMP_USERS[username]["permissions"],
        "iat": datetime.utcnow()
    }
    
    access_token = create_access_token(token_data)
    
    logger.info("User logged in successfully", username=username)
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=JWT_EXPIRATION_HOURS * 3600
    )


@router.get("/me", response_model=UserInfo)
async def get_current_user(token_data: Dict[str, Any] = Depends(verify_token)):
    """Get current user information from token."""
    
    return UserInfo(
        user_id=token_data["sub"],
        username=token_data["username"],
        permissions=token_data["permissions"]
    )


@router.post("/logout")
async def logout(token_data: Dict[str, Any] = Depends(verify_token)):
    """
    Logout user (token invalidation).
    
    Note: In a production system, you would maintain a blacklist of invalidated tokens
    or use shorter-lived tokens with refresh tokens.
    """
    username = token_data["username"]
    logger.info("User logged out", username=username)
    
    return {"message": "Successfully logged out"}


@router.post("/refresh")
async def refresh_token(token_data: Dict[str, Any] = Depends(verify_token)):
    """Refresh JWT token."""
    
    # Create new token with same data
    new_token_data = {
        "sub": token_data["sub"],
        "username": token_data["username"],
        "permissions": token_data["permissions"],
        "iat": datetime.utcnow()
    }
    
    access_token = create_access_token(new_token_data)
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=JWT_EXPIRATION_HOURS * 3600
    )


# Dependency for protected routes
def get_current_user_dependency():
    """Dependency to get current user for protected routes."""
    return Depends(verify_token)


def require_permission(permission: str):
    """Dependency factory for permission-based access control."""
    def permission_checker(token_data: Dict[str, Any] = Depends(verify_token)):
        user_permissions = token_data.get("permissions", [])
        
        if permission not in user_permissions and "admin" not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )
        
        return token_data
    
    return permission_checker