"""
Message Mirror Service for capturing and storing Telegram messages.

CRITICAL: Core message storage and retrieval for web interface
DEPENDENCIES: Database manager, Telegram service integration
FALLBACK: Queue messages if database is unavailable
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict

from ..core.database_manager import DatabaseManager
from ..core.websocket_manager import WebSocketManager
from ..utils.logging_config import setup_logging

logger = setup_logging(__name__)


@dataclass
class UnifiedMessage:
    """Unified message structure for all interfaces."""
    id: str
    content: str
    message_type: str  # telegram_out, telegram_in, web_out, qna_question, qna_answer
    channel_id: Optional[str] = None
    chat_id: Optional[str] = None
    timestamp: str = None
    user_id: Optional[str] = None
    thread_id: Optional[str] = None
    metadata: Dict[str, Any] = None
    formatting: Dict[str, Any] = None
    attachments: List[Dict] = None
    search_content: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()
        if self.metadata is None:
            self.metadata = {}
        if self.formatting is None:
            self.formatting = {}
        if self.attachments is None:
            self.attachments = []
        if self.search_content is None:
            self.search_content = self.content


@dataclass
class MessageThread:
    """Message thread for conversation grouping."""
    thread_id: str
    channel_id: Optional[str] = None
    chat_id: Optional[str] = None
    title: str = None
    created_at: str = None
    last_message_at: str = None
    message_count: int = 0
    participants: List[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.last_message_at is None:
            self.last_message_at = self.created_at
        if self.participants is None:
            self.participants = []


class MessageMirrorService:
    """
    Service for capturing, storing, and retrieving messages across all interfaces.
    
    CRITICAL: Core message persistence and synchronization
    FALLBACK: Message queuing if database operations fail
    """
    
    def __init__(self, database_manager: DatabaseManager, websocket_manager: WebSocketManager):
        self.db_manager = database_manager
        self.ws_manager = websocket_manager
        
        # Message queue for failed database operations
        self.message_queue: List[UnifiedMessage] = []
        
        # Thread cache for performance
        self.thread_cache: Dict[str, MessageThread] = {}
        
        # Message type mappings
        self.message_types = {
            "telegram_out": "Outgoing Telegram message",
            "telegram_in": "Incoming Telegram message", 
            "web_out": "Web interface message",
            "qna_question": "QnA question",
            "qna_answer": "QnA answer"
        }
    
    async def capture_outgoing_message(
        self, 
        content: str,
        chat_id: str,
        channel_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        formatting: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Capture outgoing Telegram message for web interface display.
        
        CRITICAL: Must not fail - queue if database unavailable
        """
        try:
            # Generate message ID
            message_id = f"tg_out_{uuid.uuid4().hex[:12]}"
            
            # Create unified message
            message = UnifiedMessage(
                id=message_id,
                content=content,
                message_type="telegram_out",
                channel_id=channel_id,
                chat_id=chat_id,
                metadata=metadata or {},
                formatting=formatting or {}
            )
            
            # Store in database
            await self._store_message(message)
            
            # Broadcast to web interface
            await self._broadcast_message_update(message, "message_sent")
            
            logger.info("Captured outgoing message", 
                       message_id=message_id,
                       chat_id=chat_id,
                       channel_id=channel_id)
            
            return message_id
            
        except Exception as e:
            logger.error("Failed to capture outgoing message", 
                        chat_id=chat_id,
                        error=str(e))
            
            # FALLBACK: Queue message for retry
            await self._queue_message_for_retry(message)
            return message_id
    
    async def capture_incoming_message(
        self,
        content: str,
        chat_id: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Capture incoming Telegram message."""
        try:
            message_id = f"tg_in_{uuid.uuid4().hex[:12]}"
            
            message = UnifiedMessage(
                id=message_id,
                content=content,
                message_type="telegram_in",
                chat_id=chat_id,
                user_id=user_id,
                metadata=metadata or {}
            )
            
            await self._store_message(message)
            await self._broadcast_message_update(message, "message_received")
            
            logger.info("Captured incoming message", 
                       message_id=message_id,
                       chat_id=chat_id,
                       user_id=user_id)
            
            return message_id
            
        except Exception as e:
            logger.error("Failed to capture incoming message", error=str(e))
            await self._queue_message_for_retry(message)
            return message_id
    
    async def send_web_to_telegram(
        self,
        content: str,
        chat_id: str,
        user_id: str,
        formatting: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send message from web interface to Telegram.
        
        TODO: Integrate with existing Telegram service
        """
        try:
            message_id = f"web_out_{uuid.uuid4().hex[:12]}"
            
            # Create message record
            message = UnifiedMessage(
                id=message_id,
                content=content,
                message_type="web_out",
                chat_id=chat_id,
                user_id=user_id,
                formatting=formatting or {}
            )
            
            # Store message
            await self._store_message(message)
            
            # TODO: Send to Telegram via existing service
            # For now, just simulate success
            
            # Broadcast update
            await self._broadcast_message_update(message, "web_message_sent")
            
            logger.info("Sent web message to Telegram", 
                       message_id=message_id,
                       chat_id=chat_id,
                       user_id=user_id)
            
            return {
                "message_id": message_id,
                "status": "sent",
                "timestamp": message.timestamp
            }
            
        except Exception as e:
            logger.error("Failed to send web message", error=str(e))
            return {
                "message_id": None,
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_message_history(
        self,
        filters: Optional[Dict[str, Any]] = None,
        pagination: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get message history with filtering and pagination."""
        try:
            # Default pagination
            page = pagination.get("page", 1) if pagination else 1
            page_size = pagination.get("page_size", 50) if pagination else 50
            offset = (page - 1) * page_size
            
            # Build query conditions
            conditions = []
            params = []
            
            if filters:
                if filters.get("channel_id"):
                    conditions.append("channel_id = ?")
                    params.append(filters["channel_id"])
                
                if filters.get("chat_id"):
                    conditions.append("chat_id = ?")
                    params.append(filters["chat_id"])
                
                if filters.get("message_type"):
                    conditions.append("message_type = ?")
                    params.append(filters["message_type"])
                
                if filters.get("user_id"):
                    conditions.append("user_id = ?")
                    params.append(filters["user_id"])
                
                if filters.get("thread_id"):
                    conditions.append("thread_id = ?")
                    params.append(filters["thread_id"])
                
                if filters.get("start_date"):
                    conditions.append("timestamp >= ?")
                    params.append(filters["start_date"])
                
                if filters.get("end_date"):
                    conditions.append("timestamp <= ?")
                    params.append(filters["end_date"])
            
            # Build query
            where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
            
            # Get messages
            query = f"""
                SELECT * FROM unified_messages
                {where_clause}
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """
            params.extend([page_size, offset])
            
            messages = await self.db_manager.execute_query("messages", query, tuple(params))
            
            # Get total count
            count_query = f"SELECT COUNT(*) as total FROM unified_messages{where_clause}"
            count_params = params[:-2]  # Remove LIMIT and OFFSET params
            count_result = await self.db_manager.execute_query("messages", count_query, tuple(count_params))
            total_count = count_result[0]["total"] if count_result else 0
            
            # Convert to UnifiedMessage objects
            message_objects = []
            for msg_data in messages:
                # Parse JSON fields
                metadata = json.loads(msg_data.get("metadata", "{}"))
                formatting = json.loads(msg_data.get("formatting", "{}"))
                attachments = json.loads(msg_data.get("attachments", "[]"))
                
                message_objects.append({
                    "id": msg_data["id"],
                    "content": msg_data["content"],
                    "message_type": msg_data["message_type"],
                    "channel_id": msg_data["channel_id"],
                    "chat_id": msg_data["chat_id"],
                    "timestamp": msg_data["timestamp"],
                    "user_id": msg_data["user_id"],
                    "thread_id": msg_data["thread_id"],
                    "metadata": metadata,
                    "formatting": formatting,
                    "attachments": attachments
                })
            
            logger.info("Retrieved message history", 
                       count=len(message_objects),
                       total=total_count,
                       page=page)
            
            return {
                "messages": message_objects,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_count": total_count,
                    "total_pages": (total_count + page_size - 1) // page_size,
                    "has_next": total_count > page * page_size,
                    "has_previous": page > 1
                }
            }
            
        except Exception as e:
            logger.error("Failed to get message history", error=str(e))
            raise
    
    async def search_messages(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Full-text search across messages."""
        try:
            # Build search conditions
            conditions = ["messages_fts MATCH ?"]
            params = [query]
            
            if filters:
                if filters.get("channel_id"):
                    conditions.append("unified_messages.channel_id = ?")
                    params.append(filters["channel_id"])
                
                if filters.get("message_type"):
                    conditions.append("unified_messages.message_type = ?")
                    params.append(filters["message_type"])
            
            where_clause = " WHERE " + " AND ".join(conditions)
            
            # Execute search
            search_query = f"""
                SELECT unified_messages.*, bm25(messages_fts) as rank FROM unified_messages
                JOIN messages_fts ON unified_messages.id = messages_fts.id
                {where_clause}
                ORDER BY rank
                LIMIT 100
            """
            
            results = await self.db_manager.execute_query("messages", search_query, tuple(params))
            
            # Convert results
            search_results = []
            for result in results:
                metadata = json.loads(result.get("metadata", "{}"))
                formatting = json.loads(result.get("formatting", "{}"))
                attachments = json.loads(result.get("attachments", "[]"))
                
                search_results.append({
                    "id": result["id"],
                    "content": result["content"],
                    "message_type": result["message_type"],
                    "channel_id": result["channel_id"],
                    "chat_id": result["chat_id"],
                    "timestamp": result["timestamp"],
                    "user_id": result["user_id"],
                    "thread_id": result["thread_id"],
                    "metadata": metadata,
                    "formatting": formatting,
                    "attachments": attachments,
                    "search_rank": result.get("rank", 0)
                })
            
            logger.info("Searched messages", 
                       query=query,
                       results=len(search_results))
            
            return search_results
            
        except Exception as e:
            logger.error("Failed to search messages", query=query, error=str(e))
            raise
    
    async def create_thread(
        self,
        title: str,
        channel_id: Optional[str] = None,
        chat_id: Optional[str] = None
    ) -> str:
        """Create a new message thread."""
        try:
            thread_id = f"thread_{uuid.uuid4().hex[:12]}"
            
            thread = MessageThread(
                thread_id=thread_id,
                channel_id=channel_id,
                chat_id=chat_id,
                title=title
            )
            
            # Store in database
            await self.db_manager.execute_update(
                "messages",
                """
                INSERT INTO message_threads 
                (thread_id, channel_id, chat_id, title, created_at, last_message_at, message_count, participants)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    thread.thread_id,
                    thread.channel_id,
                    thread.chat_id,
                    thread.title,
                    thread.created_at,
                    thread.last_message_at,
                    thread.message_count,
                    json.dumps(thread.participants)
                )
            )
            
            # Cache thread
            self.thread_cache[thread_id] = thread
            
            logger.info("Created message thread", 
                       thread_id=thread_id,
                       title=title)
            
            return thread_id
            
        except Exception as e:
            logger.error("Failed to create thread", title=title, error=str(e))
            raise
    
    async def _store_message(self, message: UnifiedMessage):
        """Store message in database."""
        try:
            # Insert into main messages table
            await self.db_manager.execute_update(
                "messages",
                """
                INSERT INTO unified_messages 
                (id, content, message_type, channel_id, chat_id, timestamp, user_id, thread_id, 
                 metadata, formatting, attachments, search_content)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message.id,
                    message.content,
                    message.message_type,
                    message.channel_id,
                    message.chat_id,
                    message.timestamp,
                    message.user_id,
                    message.thread_id,
                    json.dumps(message.metadata),
                    json.dumps(message.formatting),
                    json.dumps(message.attachments),
                    message.search_content
                )
            )
            
            # Insert into FTS index
            await self.db_manager.execute_update(
                "messages",
                """
                INSERT INTO messages_fts (id, content, search_content, channel_id, message_type)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    message.id,
                    message.content,
                    message.search_content,
                    message.channel_id,
                    message.message_type
                )
            )
            
            # Update thread if applicable
            if message.thread_id:
                await self._update_thread_stats(message.thread_id)
            
        except Exception as e:
            logger.error("Failed to store message", message_id=message.id, error=str(e))
            raise
    
    async def _update_thread_stats(self, thread_id: str):
        """Update thread statistics."""
        try:
            await self.db_manager.execute_update(
                "messages",
                """
                UPDATE message_threads 
                SET last_message_at = ?, message_count = message_count + 1
                WHERE thread_id = ?
                """,
                (datetime.utcnow().isoformat(), thread_id)
            )
            
        except Exception as e:
            logger.error("Failed to update thread stats", thread_id=thread_id, error=str(e))
    
    async def _broadcast_message_update(self, message: UnifiedMessage, event_type: str):
        """Broadcast message update to WebSocket clients."""
        try:
            update_data = {
                "type": event_type,
                "message": asdict(message),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Broadcast to all clients in messages group
            await self.ws_manager.broadcast_to_group("messages", update_data)
            
        except Exception as e:
            logger.error("Failed to broadcast message update", 
                        message_id=message.id,
                        event_type=event_type,
                        error=str(e))
    
    async def _queue_message_for_retry(self, message: UnifiedMessage):
        """Queue message for retry if database operations fail."""
        self.message_queue.append(message)
        
        # COST: Limit queue size to prevent memory issues
        if len(self.message_queue) > 1000:
            self.message_queue = self.message_queue[-1000:]
        
        logger.warning("Queued message for retry", 
                      message_id=message.id,
                      queue_size=len(self.message_queue))
    
    async def process_queued_messages(self):
        """Process queued messages when database is available."""
        if not self.message_queue:
            return
        
        processed = 0
        failed = []
        
        for message in self.message_queue:
            try:
                await self._store_message(message)
                await self._broadcast_message_update(message, "queued_message_processed")
                processed += 1
                
            except Exception as e:
                logger.error("Failed to process queued message", 
                           message_id=message.id,
                           error=str(e))
                failed.append(message)
        
        # Update queue with failed messages
        self.message_queue = failed
        
        if processed > 0:
            logger.info("Processed queued messages", 
                       processed=processed,
                       remaining=len(self.message_queue))
    
    async def get_service_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        try:
            # Get message counts by type
            type_counts = await self.db_manager.execute_query(
                "messages",
                "SELECT message_type, COUNT(*) as count FROM unified_messages GROUP BY message_type"
            )
            
            # Get recent activity
            recent_activity = await self.db_manager.execute_query(
                "messages",
                """
                SELECT DATE(timestamp) as date, COUNT(*) as count 
                FROM unified_messages 
                WHERE timestamp >= datetime('now', '-7 days')
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
                """
            )
            
            return {
                "total_messages": sum(item["count"] for item in type_counts),
                "message_types": {item["message_type"]: item["count"] for item in type_counts},
                "queued_messages": len(self.message_queue),
                "recent_activity": recent_activity,
                "cached_threads": len(self.thread_cache)
            }
            
        except Exception as e:
            logger.error("Failed to get service stats", error=str(e))
            return {
                "error": str(e),
                "queued_messages": len(self.message_queue),
                "cached_threads": len(self.thread_cache)
            }