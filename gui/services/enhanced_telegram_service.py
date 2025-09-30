import os
import asyncio
import json
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
import aiohttp
from dataclasses import dataclass
from enum import Enum
import logging

from ..utils.logging_config import LoggerFactory
from ..core.websocket_manager import WebSocketManager
from ..core.message_queue_manager import MessageQueueManager, PersistentQueuedMessage, QueueStatus
from .message_mirror_service import MessageMirrorService

logger = LoggerFactory.create_logger(__name__)

class MessageType(Enum):
    """Message types for queue management"""
    OUTBOUND = "outbound"
    INBOUND = "inbound"
    QNA_RESPONSE = "qna_response"
    SYSTEM_NOTIFICATION = "system_notification"

@dataclass
class QueuedMessage:
    """Represents a message in the delivery queue"""
    id: str
    chat_id: str
    message_type: MessageType
    content: str
    parse_mode: Optional[str] = "HTML"
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}

@dataclass
class TelegramChat:
    """Represents a Telegram chat configuration"""
    chat_id: str
    chat_name: str
    bot_token: str
    is_active: bool = True
    webhook_url: Optional[str] = None
    last_message_id: Optional[int] = None

class EnhancedTelegramService:
    """
    Enhanced Telegram service with bidirectional communication support.
    
    Features:
    - Webhook handling for incoming messages
    - Message queue system for reliable delivery
    - Multiple chat management
    - Integration with WebSocket for real-time updates
    - QnA conversation mirroring
    
    CRITICAL: Core communication pipeline for GUI platform
    DEPENDENCIES: aiohttp, WebSocketManager, message queue
    FALLBACK: Queue messages when Telegram unavailable
    """
    
    def __init__(self, websocket_manager: WebSocketManager, 
                 message_mirror_service: MessageMirrorService = None,
                 queue_manager: MessageQueueManager = None):
        self.websocket_manager = websocket_manager
        self.message_mirror_service = message_mirror_service
        self.queue_manager = queue_manager or MessageQueueManager()
        self.chats: Dict[str, TelegramChat] = {}
        self.message_queue: List[QueuedMessage] = []
        self.webhook_handlers: Dict[str, Callable] = {}
        self.is_running = False
        self._queue_processor_task = None
        
        # Load chat configurations from environment
        self._load_chat_configurations()
        
    def _load_chat_configurations(self):
        """Load Telegram chat configurations from environment variables"""
        # SECURITY: Load bot tokens from environment
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if bot_token and chat_id:
            # Default chat configuration
            default_chat = TelegramChat(
                chat_id=chat_id,
                chat_name="Default Chat",
                bot_token=bot_token
            )
            self.chats[chat_id] = default_chat
            logger.info("Loaded default Telegram chat configuration", chat_id=chat_id)
        
        # Load additional chats from environment (TELEGRAM_CHAT_2_ID, etc.)
        chat_index = 2
        while True:
            additional_token = os.getenv(f'TELEGRAM_BOT_TOKEN_{chat_index}')
            additional_chat_id = os.getenv(f'TELEGRAM_CHAT_ID_{chat_index}')
            
            if not (additional_token and additional_chat_id):
                break
                
            chat_name = os.getenv(f'TELEGRAM_CHAT_NAME_{chat_index}', f"Chat {chat_index}")
            additional_chat = TelegramChat(
                chat_id=additional_chat_id,
                chat_name=chat_name,
                bot_token=additional_token
            )
            self.chats[additional_chat_id] = additional_chat
            logger.info("Loaded additional Telegram chat", chat_id=additional_chat_id, name=chat_name)
            chat_index += 1
    
    async def start(self):
        """Start the enhanced Telegram service"""
        if self.is_running:
            return
            
        self.is_running = True
        
        # Start persistent message queue manager
        await self.queue_manager.start()
        
        # Start message queue processor
        self._queue_processor_task = asyncio.create_task(self._process_message_queue())
        
        # Set up webhooks for all configured chats
        await self._setup_webhooks()
        
        logger.info("Enhanced Telegram service started", chat_count=len(self.chats))
    
    async def stop(self):
        """Stop the enhanced Telegram service"""
        self.is_running = False
        
        if self._queue_processor_task:
            self._queue_processor_task.cancel()
            try:
                await self._queue_processor_task
            except asyncio.CancelledError:
                pass
        
        # Stop persistent queue manager
        await self.queue_manager.stop()
        
        # Remove webhooks
        await self._cleanup_webhooks()
        
        logger.info("Enhanced Telegram service stopped")
    
    async def _setup_webhooks(self):
        """Set up webhooks for all configured chats"""
        for chat_id, chat in self.chats.items():
            if not chat.is_active:
                continue
                
            try:
                # DECISION: Use webhook URL from environment or generate default
                webhook_url = os.getenv(f'TELEGRAM_WEBHOOK_URL_{chat_id}') or \
                             os.getenv('TELEGRAM_WEBHOOK_URL', f"https://your-domain.com/webhook/telegram/{chat_id}")
                
                await self._set_webhook(chat.bot_token, webhook_url)
                chat.webhook_url = webhook_url
                logger.info("Webhook set up successfully", chat_id=chat_id, webhook_url=webhook_url)
                
            except Exception as e:
                logger.error("Failed to set up webhook", chat_id=chat_id, error=str(e))
    
    async def _cleanup_webhooks(self):
        """Remove webhooks for all configured chats"""
        for chat_id, chat in self.chats.items():
            try:
                await self._delete_webhook(chat.bot_token)
                logger.info("Webhook removed", chat_id=chat_id)
            except Exception as e:
                logger.error("Failed to remove webhook", chat_id=chat_id, error=str(e))    

    async def _set_webhook(self, bot_token: str, webhook_url: str):
        """Set webhook for a specific bot"""
        url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
        data = {
            "url": webhook_url,
            "allowed_updates": ["message", "callback_query"]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                if response.status != 200:
                    raise Exception(f"Failed to set webhook: {await response.text()}")
    
    async def _delete_webhook(self, bot_token: str):
        """Delete webhook for a specific bot"""
        url = f"https://api.telegram.org/bot{bot_token}/deleteWebhook"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url) as response:
                if response.status != 200:
                    raise Exception(f"Failed to delete webhook: {await response.text()}")
    
    def add_chat(self, chat_id: str, chat_name: str, bot_token: str) -> bool:
        """Add a new Telegram chat configuration"""
        try:
            new_chat = TelegramChat(
                chat_id=chat_id,
                chat_name=chat_name,
                bot_token=bot_token
            )
            self.chats[chat_id] = new_chat
            logger.info("Added new Telegram chat", chat_id=chat_id, name=chat_name)
            return True
        except Exception as e:
            logger.error("Failed to add chat", chat_id=chat_id, error=str(e))
            return False
    
    def remove_chat(self, chat_id: str) -> bool:
        """Remove a Telegram chat configuration"""
        try:
            if chat_id in self.chats:
                chat = self.chats[chat_id]
                chat.is_active = False
                logger.info("Deactivated Telegram chat", chat_id=chat_id)
                return True
            return False
        except Exception as e:
            logger.error("Failed to remove chat", chat_id=chat_id, error=str(e))
            return False
    
    def get_active_chats(self) -> List[TelegramChat]:
        """Get list of active Telegram chats"""
        return [chat for chat in self.chats.values() if chat.is_active]
    
    async def send_message_to_chat(self, chat_id: str, message: str, 
                                  message_type: MessageType = MessageType.OUTBOUND,
                                  parse_mode: str = "HTML",
                                  channel_id: str = None) -> bool:
        """Send message to specific Telegram chat with persistent queueing"""
        if chat_id not in self.chats or not self.chats[chat_id].is_active:
            logger.error("Chat not found or inactive", chat_id=chat_id)
            return False
        
        # Create persistent queued message
        persistent_msg = PersistentQueuedMessage(
            id=f"{chat_id}_{datetime.utcnow().timestamp()}",
            chat_id=chat_id,
            message_type=message_type.value,
            content=message,
            parse_mode=parse_mode,
            metadata={"channel_id": channel_id} if channel_id else {}
        )
        
        # Queue in persistent storage
        success = self.queue_manager.enqueue_message(persistent_msg)
        
        if success:
            # Mirror to web interface immediately
            if self.message_mirror_service:
                try:
                    await self.message_mirror_service.capture_outgoing_message(
                        content=message,
                        chat_id=chat_id,
                        channel_id=channel_id,
                        metadata={"message_type": message_type.value, "parse_mode": parse_mode}
                    )
                except Exception as e:
                    logger.error("Failed to mirror outgoing message", error=str(e))
            
            logger.info("Message queued for delivery", chat_id=chat_id, message_type=message_type.value)
        
        return success
    
    async def send_message_to_all_chats(self, message: str, 
                                       message_type: MessageType = MessageType.OUTBOUND,
                                       parse_mode: str = "HTML",
                                       channel_id: str = None) -> Dict[str, bool]:
        """Send message to all active Telegram chats"""
        results = {}
        
        for chat_id in self.chats:
            if self.chats[chat_id].is_active:
                success = await self.send_message_to_chat(
                    chat_id, message, message_type, parse_mode, channel_id
                )
                results[chat_id] = success
        
        return results
    
    async def _process_message_queue(self):
        """Process persistent message queue"""
        while self.is_running:
            try:
                # Get pending messages from persistent queue
                pending_messages = self.queue_manager.get_pending_messages(limit=5)
                
                if not pending_messages:
                    await asyncio.sleep(1)
                    continue
                
                # Process each message
                for message in pending_messages:
                    try:
                        # Mark as processing
                        self.queue_manager.update_message_status(message.id, QueueStatus.PROCESSING)
                        
                        # Deliver message
                        success = await self._deliver_persistent_message(message)
                        
                        if success:
                            # Mark as delivered
                            self.queue_manager.update_message_status(message.id, QueueStatus.DELIVERED)
                            logger.info("Message delivered successfully", message_id=message.id)
                        else:
                            # Handle retry logic
                            if message.retry_count < message.max_retries:
                                # Schedule retry with exponential backoff
                                delay_minutes = 2 ** message.retry_count
                                next_attempt = datetime.utcnow() + timedelta(minutes=delay_minutes)
                                
                                self.queue_manager.update_message_status(
                                    message.id, 
                                    QueueStatus.PENDING,
                                    retry_count=message.retry_count + 1,
                                    scheduled_at=next_attempt
                                )
                                logger.warning("Message delivery failed, scheduling retry", 
                                             message_id=message.id, 
                                             retry_count=message.retry_count + 1,
                                             next_attempt=next_attempt.isoformat())
                            else:
                                # Mark as permanently failed
                                self.queue_manager.update_message_status(message.id, QueueStatus.FAILED)
                                logger.error("Message delivery failed permanently", message_id=message.id)
                    
                    except Exception as e:
                        logger.error("Error processing message", message_id=message.id, error=str(e))
                        # Mark as failed
                        self.queue_manager.update_message_status(message.id, QueueStatus.FAILED)
                
                # Rate limiting
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error("Error in message queue processor", error=str(e))
                await asyncio.sleep(5)
    
    async def _deliver_persistent_message(self, message: PersistentQueuedMessage) -> bool:
        """Deliver a single persistent message to Telegram"""
        chat = self.chats.get(message.chat_id)
        if not chat or not chat.is_active:
            return False
        
        try:
            url = f"https://api.telegram.org/bot{chat.bot_token}/sendMessage"
            data = {
                "chat_id": message.chat_id,
                "text": message.content,
                "parse_mode": message.parse_mode,
                "disable_web_page_preview": True
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, timeout=30) as response:
                    if response.status == 200:
                        return True
                    else:
                        logger.error("Telegram API error", 
                                   status=response.status, 
                                   response=await response.text())
                        return False
        
        except Exception as e:
            logger.error("Failed to deliver message", message_id=message.id, error=str(e))
            return False
    
    async def _mirror_to_web_interface(self, message: QueuedMessage):
        """Mirror Telegram message to web interface via WebSocket"""
        try:
            web_message = {
                "type": "telegram_message",
                "chat_id": message.chat_id,
                "chat_name": self.chats[message.chat_id].chat_name,
                "message_type": message.message_type.value,
                "content": message.content,
                "timestamp": message.created_at.isoformat(),
                "direction": "outbound"
            }
            
            await self.websocket_manager.broadcast_to_all(web_message)
            logger.debug("Message mirrored to web interface", message_id=message.id)
            
        except Exception as e:
            logger.error("Failed to mirror message to web interface", 
                        message_id=message.id, error=str(e))
    
    def register_webhook_handler(self, message_type: str, handler: Callable):
        """Register handler for incoming webhook messages"""
        self.webhook_handlers[message_type] = handler
        logger.info("Webhook handler registered", message_type=message_type)
    
    async def handle_webhook(self, chat_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming webhook from Telegram"""
        try:
            # SECURITY: Validate chat_id exists in our configuration
            if chat_id not in self.chats:
                logger.warning("Webhook received for unknown chat", chat_id=chat_id)
                return {"status": "error", "message": "Unknown chat"}
            
            # Extract message data
            message_data = update_data.get("message", {})
            if not message_data:
                return {"status": "ignored", "message": "No message data"}
            
            # Process incoming message
            await self._process_incoming_message(chat_id, message_data)
            
            return {"status": "success", "message": "Message processed"}
            
        except Exception as e:
            logger.error("Error handling webhook", chat_id=chat_id, error=str(e))
            return {"status": "error", "message": str(e)}
    
    async def _process_incoming_message(self, chat_id: str, message_data: Dict[str, Any]):
        """Process incoming message from Telegram"""
        try:
            message_text = message_data.get("text", "")
            message_id = message_data.get("message_id")
            user_info = message_data.get("from", {})
            
            # Update last message ID
            if message_id:
                self.chats[chat_id].last_message_id = message_id
            
            # Mirror to message service for persistence
            if self.message_mirror_service and message_text.strip():
                try:
                    await self.message_mirror_service.capture_incoming_message(
                        content=message_text,
                        chat_id=chat_id,
                        user_id=str(user_info.get("id", "")),
                        metadata={
                            "telegram_message_id": message_id,
                            "user_info": user_info,
                            "chat_name": self.chats[chat_id].chat_name
                        }
                    )
                except Exception as e:
                    logger.error("Failed to mirror incoming message", error=str(e))
            
            # Create incoming message for web interface
            incoming_message = {
                "type": "telegram_message",
                "chat_id": chat_id,
                "chat_name": self.chats[chat_id].chat_name,
                "message_type": MessageType.INBOUND.value,
                "content": message_text,
                "timestamp": datetime.utcnow().isoformat(),
                "direction": "inbound",
                "user_info": {
                    "id": user_info.get("id"),
                    "username": user_info.get("username"),
                    "first_name": user_info.get("first_name"),
                    "last_name": user_info.get("last_name")
                },
                "message_id": message_id
            }
            
            # Mirror to web interface via WebSocket
            await self.websocket_manager.broadcast_to_all(incoming_message)
            
            # Check for registered handlers (QnA, commands, etc.)
            for handler_type, handler in self.webhook_handlers.items():
                try:
                    await handler(chat_id, message_text, message_data)
                except Exception as e:
                    logger.error("Error in webhook handler", 
                               handler_type=handler_type, error=str(e))
            
            logger.info("Incoming message processed", 
                       chat_id=chat_id, message_id=message_id, user_id=user_info.get("id"))
            
        except Exception as e:
            logger.error("Error processing incoming message", 
                        chat_id=chat_id, error=str(e))
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current message queue status"""
        persistent_stats = self.queue_manager.get_queue_statistics()
        
        return {
            "memory_queue_length": len(self.message_queue),
            "persistent_queue_stats": persistent_stats,
            "is_running": self.is_running,
            "active_chats": len([c for c in self.chats.values() if c.is_active]),
            "total_chats": len(self.chats),
            "webhook_handlers": len(self.webhook_handlers)
        }
    
    def clear_queue(self) -> int:
        """Clear message queue and return number of cleared messages"""
        cleared_count = len(self.message_queue)
        self.message_queue.clear()
        logger.info("Message queue cleared", cleared_count=cleared_count)
        return cleared_count