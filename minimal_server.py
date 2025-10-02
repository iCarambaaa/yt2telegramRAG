#!/usr/bin/env python3
"""Minimal server with only database router for testing."""

import sys
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add the gui directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gui'))

# Create FastAPI app
app = FastAPI(
    title="Minimal Database Server",
    description="Testing database router only",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Import and include database router
try:
    from api.routers.database import router as database_router
    app.include_router(database_router, prefix="/api/database", tags=["database"])
    print("✓ Database router included successfully")
except Exception as e:
    print(f"✗ Failed to include database router: {e}")
    import traceback
    traceback.print_exc()

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Minimal Database Server",
        "status": "operational",
        "endpoints": ["/api/database"]
    }

@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy"}

if __name__ == "__main__":
    print("Starting minimal database server...")
    print("Server: http://127.0.0.1:8001")
    print("Database API: http://127.0.0.1:8001/api/database/channels")
    
    uvicorn.run(
        "minimal_server:app",
        host="127.0.0.1",
        port=8001,
        reload=False,
        log_level="info"
    )