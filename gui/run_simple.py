#!/usr/bin/env python3
"""Simplified development server for testing the GUI."""

import sys
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add the gui directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Create a simple FastAPI app for testing
app = FastAPI(
    title="Unified GUI Platform - Test Server",
    description="Simplified server for testing GUI components",
    version="1.0.0-test"
)

# Configure CORS for web interface
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "https://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Import and include routers
try:
    from api.routers.qna import router as qna_router
    app.include_router(qna_router, prefix="/api/qna", tags=["qna"])
    print("✓ QnA router included")
except Exception as e:
    print(f"⚠ Failed to include QnA router: {e}")

try:
    from api.routers.channels import router as channels_router
    app.include_router(channels_router, prefix="/api/channels", tags=["channels"])
    print("✓ Channels router included")
except Exception as e:
    print(f"⚠ Failed to include channels router: {e}")

try:
    from api.routers.messages import router as messages_router
    app.include_router(messages_router, prefix="/api/messages", tags=["messages"])
    print("✓ Messages router included")
except Exception as e:
    print(f"⚠ Failed to include messages router: {e}")

try:
    from api.routers.analytics import router as analytics_router
    app.include_router(analytics_router, prefix="/api/analytics", tags=["analytics"])
    print("✓ Analytics router included")
except Exception as e:
    print(f"⚠ Failed to include analytics router: {e}")

try:
    from api.routers.auth import router as auth_router
    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
    print("✓ Auth router included")
except Exception as e:
    print(f"⚠ Failed to include auth router: {e}")

try:
    from api.routers.database import router as database_router
    app.include_router(database_router, prefix="/api/database", tags=["database"])
    print("✓ Database router included")
except Exception as e:
    print(f"⚠ Failed to include database router: {e}")

@app.get("/")
async def root():
    """Root endpoint."""
    # Get actual registered routes
    registered_routes = []
    for route in app.routes:
        if hasattr(route, 'path') and route.path.startswith('/api/'):
            prefix = route.path.split('/')[1:3]  # Get /api/prefix
            route_prefix = f"/{'/'.join(prefix)}"
            if route_prefix not in registered_routes:
                registered_routes.append(route_prefix)
    
    return {
        "message": "Unified GUI Platform - Test Server",
        "version": "1.0.0-test",
        "status": "operational",
        "endpoints": sorted(registered_routes) if registered_routes else [
            "/api/qna",
            "/api/channels", 
            "/api/messages",
            "/api/analytics",
            "/api/auth",
            "/api/database"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "message": "Test server is running"
    }

if __name__ == "__main__":
    print("Starting Unified GUI Platform Test Server...")
    print("Server will be available at: http://127.0.0.1:8000")
    print("API documentation at: http://127.0.0.1:8000/docs")
    
    uvicorn.run(
        "run_simple:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )