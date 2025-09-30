from fastapi import APIRouter, HTTPException, Request, Depends
from typing import Dict, Any
import logging

from ...services.enhanced_telegram_service import EnhancedTelegramService
from ...core.websocket_manager import WebSocketManager
from ...utils.logging_config import LoggerFactory

logger = LoggerFactory.create_logger(__name__)

router = APIRouter(prefix="/webhook/telegram", tags=["telegram"])

# CRITICAL: Webhook endpoint for Telegram integration
# SECURITY: Validate incoming webhook requests
# DEPENDENCIES: EnhancedTelegramService, WebSocketManager

async def get_telegram_service() -> EnhancedTelegramService:
    """Dependency to get Telegram service instance"""
    from ...main import get_enhanced_telegram_service
    return get_enhanced_telegram_service()

@router.post("/{chat_id}")
async def telegram_webhook(
    chat_id: str,
    request: Request,
    telegram_service: EnhancedTelegramService = Depends(get_telegram_service)
):
    """
    Handle incoming Telegram webhook updates.
    
    CRITICAL: Main entry point for bidirectional Telegram communication
    SECURITY: Validates chat_id against configured chats
    FALLBACK: Returns error for unknown chats
    
    Args:
        chat_id: Telegram chat ID from URL path
        request: FastAPI request object containing webhook data
        telegram_service: Injected Telegram service instance
    
    Returns:
        Dict with processing status
    """
    try:
        if not telegram_service:
            logger.error("Telegram service not available")
            raise HTTPException(status_code=503, detail="Telegram service unavailable")
        
        # Get webhook data
        update_data = await request.json()
        
        # SECURITY: Log webhook reception (without sensitive data)
        logger.info("Webhook received", 
                   chat_id=chat_id, 
                   update_type=list(update_data.keys()))
        
        # Process webhook through service
        result = await telegram_service.handle_webhook(chat_id, update_data)
        
        if result["status"] == "error":
            logger.error("Webhook processing failed", 
                        chat_id=chat_id, 
                        error=result["message"])
            raise HTTPException(status_code=400, detail=result["message"])
        
        return result
        
    except Exception as e:
        logger.error("Webhook handler error", chat_id=chat_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{chat_id}/status")
async def get_chat_status(
    chat_id: str,
    telegram_service: EnhancedTelegramService = Depends(get_telegram_service)
):
    """
    Get status of a specific Telegram chat.
    
    Args:
        chat_id: Telegram chat ID
        telegram_service: Injected Telegram service instance
    
    Returns:
        Dict with chat status information
    """
    try:
        if not telegram_service:
            raise HTTPException(status_code=503, detail="Telegram service unavailable")
        
        chat = telegram_service.chats.get(chat_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        
        return {
            "chat_id": chat.chat_id,
            "chat_name": chat.chat_name,
            "is_active": chat.is_active,
            "webhook_url": chat.webhook_url,
            "last_message_id": chat.last_message_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting chat status", chat_id=chat_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/{chat_id}/send")
async def send_message_to_chat(
    chat_id: str,
    message_data: Dict[str, Any],
    telegram_service: EnhancedTelegramService = Depends(get_telegram_service)
):
    """
    Send message to specific Telegram chat via API.
    
    DECISION: Allow web interface to send messages to Telegram
    SECURITY: Validate message content and chat permissions
    
    Args:
        chat_id: Target Telegram chat ID
        message_data: Message content and options
        telegram_service: Injected Telegram service instance
    
    Returns:
        Dict with send status
    """
    try:
        if not telegram_service:
            raise HTTPException(status_code=503, detail="Telegram service unavailable")
        
        message = message_data.get("message", "")
        parse_mode = message_data.get("parse_mode", "HTML")
        
        if not message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        # SECURITY: Basic message validation
        if len(message) > 4096:
            raise HTTPException(status_code=400, detail="Message too long")
        
        success = await telegram_service.send_message_to_chat(
            chat_id=chat_id,
            message=message,
            parse_mode=parse_mode
        )
        
        if success:
            return {"status": "success", "message": "Message queued for delivery"}
        else:
            raise HTTPException(status_code=400, detail="Failed to queue message")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error sending message", chat_id=chat_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/queue/status")
async def get_queue_status(
    telegram_service: EnhancedTelegramService = Depends(get_telegram_service)
):
    """
    Get current message queue status.
    
    Returns:
        Dict with queue statistics
    """
    try:
        if not telegram_service:
            raise HTTPException(status_code=503, detail="Telegram service unavailable")
        
        return telegram_service.get_queue_status()
        
    except Exception as e:
        logger.error("Error getting queue status", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/queue/clear")
async def clear_message_queue(
    telegram_service: EnhancedTelegramService = Depends(get_telegram_service)
):
    """
    Clear the message queue (admin operation).
    
    SECURITY: Should be protected by admin authentication
    
    Returns:
        Dict with number of cleared messages
    """
    try:
        if not telegram_service:
            raise HTTPException(status_code=503, detail="Telegram service unavailable")
        
        cleared_count = telegram_service.clear_queue()
        
        return {
            "status": "success",
            "cleared_messages": cleared_count
        }
        
    except Exception as e:
        logger.error("Error clearing queue", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/chats")
async def list_active_chats(
    telegram_service: EnhancedTelegramService = Depends(get_telegram_service)
):
    """
    List all active Telegram chats.
    
    Returns:
        List of active chat configurations
    """
    try:
        if not telegram_service:
            raise HTTPException(status_code=503, detail="Telegram service unavailable")
        
        active_chats = telegram_service.get_active_chats()
        
        return {
            "chats": [
                {
                    "chat_id": chat.chat_id,
                    "chat_name": chat.chat_name,
                    "is_active": chat.is_active,
                    "webhook_url": chat.webhook_url,
                    "last_message_id": chat.last_message_id
                }
                for chat in active_chats
            ]
        }
        
    except Exception as e:
        logger.error("Error listing chats", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")