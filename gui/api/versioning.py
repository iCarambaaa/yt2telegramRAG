"""
API versioning and compatibility management.

CRITICAL: API version management and backward compatibility
"""

from fastapi import APIRouter, Request, HTTPException, status
from typing import Dict, Any, Optional
import re
from packaging import version

from utils.logging_config import setup_logging

logger = setup_logging(__name__)


class APIVersionManager:
    """
    Manages API versioning and compatibility.
    
    CRITICAL: Ensures backward compatibility across API versions
    """
    
    def __init__(self):
        self.supported_versions = ["1.0", "1.1"]
        self.default_version = "1.0"
        self.deprecated_versions = []
        
        # Version-specific feature flags
        self.version_features = {
            "1.0": {
                "basic_auth": True,
                "websocket_support": True,
                "message_mirror": True,
                "qna_basic": True
            },
            "1.1": {
                "basic_auth": True,
                "websocket_support": True,
                "message_mirror": True,
                "qna_basic": True,
                "ai_enhanced": True,
                "advanced_analytics": True,
                "bulk_operations": True
            }
        }
    
    def extract_version_from_path(self, path: str) -> Optional[str]:
        """Extract API version from request path."""
        match = re.match(r'/api/v(\d+(?:\.\d+)?)', path)
        return match.group(1) if match else None
    
    def extract_version_from_header(self, request: Request) -> Optional[str]:
        """Extract API version from Accept header."""
        accept_header = request.headers.get("Accept", "")
        match = re.search(r'application/vnd\.gui\.v(\d+(?:\.\d+)?)', accept_header)
        return match.group(1) if match else None
    
    def get_request_version(self, request: Request) -> str:
        """Determine API version for request."""
        # Priority: path > header > default
        api_version = (
            self.extract_version_from_path(request.url.path) or
            self.extract_version_from_header(request) or
            self.default_version
        )
        
        return api_version
    
    def validate_version(self, api_version: str) -> bool:
        """Validate if API version is supported."""
        return api_version in self.supported_versions
    
    def is_version_deprecated(self, api_version: str) -> bool:
        """Check if API version is deprecated."""
        return api_version in self.deprecated_versions
    
    def get_version_features(self, api_version: str) -> Dict[str, bool]:
        """Get feature flags for API version."""
        return self.version_features.get(api_version, {})
    
    def check_feature_availability(self, api_version: str, feature: str) -> bool:
        """Check if feature is available in API version."""
        features = self.get_version_features(api_version)
        return features.get(feature, False)
    
    def create_versioned_router(self, version: str, prefix: str = "") -> APIRouter:
        """Create router for specific API version."""
        router = APIRouter(prefix=f"/api/v{version}{prefix}")
        
        # Add version info to router
        router.version = version
        router.features = self.get_version_features(version)
        
        return router
    
    def get_compatibility_info(self) -> Dict[str, Any]:
        """Get API compatibility information."""
        return {
            "supported_versions": self.supported_versions,
            "default_version": self.default_version,
            "deprecated_versions": self.deprecated_versions,
            "latest_version": max(self.supported_versions, key=version.parse),
            "version_features": self.version_features
        }


# Global version manager instance
version_manager = APIVersionManager()


def require_feature(feature_name: str):
    """Dependency to require specific feature availability."""
    def feature_checker(request: Request):
        api_version = version_manager.get_request_version(request)
        
        if not version_manager.validate_version(api_version):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported API version: {api_version}"
            )
        
        if not version_manager.check_feature_availability(api_version, feature_name):
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"Feature '{feature_name}' not available in API version {api_version}"
            )
        
        # Add version info to request state
        request.state.api_version = api_version
        request.state.api_features = version_manager.get_version_features(api_version)
        
        return api_version
    
    return feature_checker


def get_api_version(request: Request) -> str:
    """Dependency to get API version for request."""
    api_version = version_manager.get_request_version(request)
    
    if not version_manager.validate_version(api_version):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported API version: {api_version}"
        )
    
    # Log deprecated version usage
    if version_manager.is_version_deprecated(api_version):
        logger.warning("Deprecated API version used", 
                      version=api_version,
                      path=request.url.path)
    
    # Add version info to request state
    request.state.api_version = api_version
    request.state.api_features = version_manager.get_version_features(api_version)
    
    return api_version


# Create version-specific routers
v1_router = version_manager.create_versioned_router("1.0")
v1_1_router = version_manager.create_versioned_router("1.1")


@v1_router.get("/info")
async def get_v1_info():
    """Get API v1.0 information."""
    return {
        "version": "1.0",
        "features": version_manager.get_version_features("1.0"),
        "status": "stable"
    }


@v1_1_router.get("/info")
async def get_v1_1_info():
    """Get API v1.1 information."""
    return {
        "version": "1.1", 
        "features": version_manager.get_version_features("1.1"),
        "status": "stable"
    }


# Compatibility endpoint
compatibility_router = APIRouter(prefix="/api")


@compatibility_router.get("/compatibility")
async def get_compatibility_info():
    """Get API compatibility information."""
    return version_manager.get_compatibility_info()