"""
Main FastAPI application for the Unified GUI Platform.

CRITICAL: Core application entry point - failures affect all users
DEPENDENCIES: FastAPI, SQLite, WebSocket, Redis
FALLBACK: Graceful degradation to basic functionality if advanced features fail
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
from typing import Dict, List

from .api.router_registry import create_enhanced_routers, registry_router
from .api.versioning import compatibility_router
from .core.websocket_manager import WebSocketManager
from .core.database_manager import DatabaseManager
from .core.connection_pool import EnhancedDatabaseManager
from .core.middleware import (
    AuthenticationMiddleware, 
    RequestLoggingMiddleware, 
    RateLimitingMiddleware,
    ErrorHandlingMiddleware
)
from .services.message_mirror_service import MessageMirrorService
from .services.enhanced_telegram_service import EnhancedTelegramService
from .services.telegram_qna_handler import TelegramQnAHandler
from .core.message_queue_manager import MessageQueueManager
from .utils.logging_config import setup_logging

# Initialize logging
logger = setup_logging(__name__)

# Global managers
websocket_manager = WebSocketManager()
database_manager = EnhancedDatabaseManager()  # Use enhanced database manager
message_mirror_service = None  # Will be initialized in lifespan
enhanced_telegram_service = None  # Will be initialized in lifespan
telegram_qna_handler = None  # Will be initialized in lifespan
message_queue_manager = None  # Will be initialized in lifespan


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    # CRITICAL: Initialize core services on startup
    logger.info("Starting Unified GUI Platform")
    
    global message_mirror_service, enhanced_telegram_service, telegram_qna_handler, message_queue_manager
    
    try:
        # Initialize database connections
        await database_manager.initialize()
        logger.info("Database manager initialized successfully")
        
        # Initialize WebSocket manager
        await websocket_manager.initialize()
        logger.info("WebSocket manager initialized successfully")
        
        # Initialize message queue manager
        message_queue_manager = MessageQueueManager()
        await message_queue_manager.start()
        logger.info("Message queue manager initialized successfully")
        
        # Initialize message mirror service
        message_mirror_service = MessageMirrorService(database_manager, websocket_manager)
        logger.info("Message mirror service initialized successfully")
        
        # Initialize message service in API routes
        from .api.routers.messages import initialize_message_service
        initialize_message_service(database_manager, websocket_manager)
        
        # Initialize enhanced Telegram service
        enhanced_telegram_service = EnhancedTelegramService(
            websocket_manager=websocket_manager,
            message_mirror_service=message_mirror_service,
            queue_manager=message_queue_manager
        )
        await enhanced_telegram_service.start()
        logger.info("Enhanced Telegram service initialized successfully")
        
        # Initialize Telegram QnA handler
        telegram_qna_handler = TelegramQnAHandler(enhanced_telegram_service)
        logger.info("Telegram QnA handler initialized successfully")
        
        # Add authentication middleware after database is initialized
        from .api.routers.auth import JWT_SECRET_KEY, JWT_ALGORITHM
        app.add_middleware(AuthenticationMiddleware, 
                          jwt_secret=JWT_SECRET_KEY, 
                          jwt_algorithm=JWT_ALGORITHM)
        
        yield
        
    except Exception as e:
        logger.error("Failed to initialize core services", error=str(e))
        # FALLBACK: Continue with limited functionality
        yield
    
    finally:
        # Cleanup on shutdown
        logger.info("Shutting down Unified GUI Platform")
        
        if enhanced_telegram_service:
            await enhanced_telegram_service.stop()
            logger.info("Enhanced Telegram service stopped")
        
        if message_queue_manager:
            await message_queue_manager.stop()
            logger.info("Message queue manager stopped")
        
        await websocket_manager.cleanup()
        await database_manager.cleanup()


# Create FastAPI application
app = FastAPI(
    title="Unified GUI Platform",
    description="Comprehensive management interface for YouTube to Telegram system",
    version="1.0.0",
    lifespan=lifespan
)

# SECURITY: Configure CORS for web interface
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://127.0.0.1:3000",  # React dev server
        "http://localhost:8080",  # Alternative dev port
        "https://localhost:3000"  # HTTPS dev
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# SECURITY: Add enhanced middleware stack
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(RateLimitingMiddleware, requests_per_minute=120)  # Allow higher rate for GUI
app.add_middleware(RequestLoggingMiddleware, database_manager=database_manager)
# Note: AuthenticationMiddleware is added after database_manager is initialized

# Create and register enhanced routers with versioning
router_registry = create_enhanced_routers()
app_routers = router_registry.create_versioned_app_routers(app)

# Include utility routers
app.include_router(registry_router, tags=["registry"])
app.include_router(compatibility_router, tags=["compatibility"])

# Serve static files for web interface
app.mount("/static", StaticFiles(directory="gui/static"), name="static")


@app.get("/")
async def root():
    """Root endpoint with system status."""
    return {
        "message": "Unified GUI Platform",
        "version": "1.0.0",
        "status": "operational",
        "features": [
            "Traditional GUI",
            "AI Conversational Interface", 
            "Telegram Message Mirror",
            "Integrated QnA System",
            "Real-time Synchronization"
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    try:
        # Check database connectivity
        db_status = await database_manager.health_check()
        
        # Check WebSocket manager
        ws_status = websocket_manager.get_status()
        
        return {
            "status": "healthy",
            "database": db_status,
            "websocket": ws_status,
            "timestamp": database_manager.get_current_timestamp()
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": database_manager.get_current_timestamp()
        }


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    WebSocket endpoint for real-time communication.
    
    CRITICAL: Real-time synchronization across all interfaces
    FALLBACK: Graceful handling of connection failures
    """
    try:
        await websocket_manager.connect(websocket, client_id)
        logger.info("WebSocket client connected", client_id=client_id)
        
        while True:
            # Listen for messages from client
            data = await websocket.receive_text()
            await websocket_manager.handle_message(client_id, data)
            
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected", client_id=client_id)
        await websocket_manager.disconnect(client_id)
    except Exception as e:
        logger.error("WebSocket error", client_id=client_id, error=str(e))
        await websocket_manager.disconnect(client_id)


# Dependency functions for services
def get_database_manager() -> DatabaseManager:
    """Get database manager instance."""
    return database_manager


def get_websocket_manager() -> WebSocketManager:
    """Get WebSocket manager instance."""
    return websocket_manager


def get_message_mirror_service() -> MessageMirrorService:
    """Get message mirror service instance."""
    if message_mirror_service is None:
        raise RuntimeError("Message mirror service not initialized")
    return message_mirror_service


def get_enhanced_telegram_service() -> EnhancedTelegramService:
    """Get enhanced Telegram service instance."""
    if enhanced_telegram_service is None:
        raise RuntimeError("Enhanced Telegram service not initialized")
    return enhanced_telegram_service


def get_telegram_qna_handler() -> TelegramQnAHandler:
    """Get Telegram QnA handler instance."""
    if telegram_qna_handler is None:
        raise RuntimeError("Telegram QnA handler not initialized")
    return telegram_qna_handler


def get_message_queue_manager() -> MessageQueueManager:
    """Get message queue manager instance."""
    if message_queue_manager is None:
        raise RuntimeError("Message queue manager not initialized")
    return message_queue_manager


if __name__ == "__main__":
    import uvicorn
    
    # DECISION: Development server configuration
    uvicorn.run(
        "gui.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )