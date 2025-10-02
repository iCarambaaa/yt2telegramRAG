"""
Message mirror API endpoints for Telegram integration.

CRITICAL: Message storage and retrieval for web interface
DEPENDENCIES: Database manager, Telegram service
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from .auth import get_current_user_dependency
from utils.logging_config import setup_logging
from services.message_mirror_service import MessageMirrorService
from core.database_manager import DatabaseManager
from core.websocket_manager import WebSocketManager

logger = setup_logging(__name__)

router = APIRouter()

# Global service instances - will be injected by main app
message_mirror_service: Optional[MessageMirrorService] = None

def get_message_mirror_service() -> MessageMirrorService:
    """Dependency to get message mirror service."""
    if message_mirror_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Message mirror service not available"
        )
    return message_mirror_service


class MessageResponse(BaseModel):
    id: str
    content: str
    message_type: str
    channel_id: Optional[str]
    chat_id: Optional[str]
    timestamp: str
    user_id: Optional[str]
    thread_id: Optional[str]
    metadata: Dict[str, Any]
    formatting: Dict[str, Any]
    attachments: List[Dict]


class MessageListResponse(BaseModel):
    messages: List[MessageResponse]
    total_count: int
    page: int
    page_size: int
    has_next: bool


class SendMessageRequest(BaseModel):
    content: str
    chat_id: str
    message_type: str = "web_out"
    formatting: Optional[Dict[str, Any]] = None


@router.get("/", response_model=MessageListResponse)
async def list_messages(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    channel_id: Optional[str] = Query(None, description="Filter by channel ID"),
    chat_id: Optional[str] = Query(None, description="Filter by chat ID"),
    message_type: Optional[str] = Query(None, description="Filter by message type"),
    thread_id: Optional[str] = Query(None, description="Filter by thread ID"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    current_user: Dict = Depends(get_current_user_dependency()),
    service: MessageMirrorService = Depends(get_message_mirror_service)
):
    """List messages with pagination and filtering."""
    
    try:
        # Build filters
        filters = {}
        if channel_id:
            filters["channel_id"] = channel_id
        if chat_id:
            filters["chat_id"] = chat_id
        if message_type:
            filters["message_type"] = message_type
        if thread_id:
            filters["thread_id"] = thread_id
        if start_date:
            filters["start_date"] = start_date
        if end_date:
            filters["end_date"] = end_date
        
        # Build pagination
        pagination = {
            "page": page,
            "page_size": page_size
        }
        
        # Get message history
        result = await service.get_message_history(filters, pagination)
        
        # Convert to response format
        messages = [
            MessageResponse(
                id=msg["id"],
                content=msg["content"],
                message_type=msg["message_type"],
                channel_id=msg["channel_id"],
                chat_id=msg["chat_id"],
                timestamp=msg["timestamp"],
                user_id=msg["user_id"],
                thread_id=msg["thread_id"],
                metadata=msg["metadata"],
                formatting=msg["formatting"],
                attachments=msg["attachments"]
            )
            for msg in result["messages"]
        ]
        
        logger.info("Listed messages", 
                   page=page, 
                   page_size=page_size, 
                   total=result["pagination"]["total_count"],
                   user=current_user["username"])
        
        return MessageListResponse(
            messages=messages,
            total_count=result["pagination"]["total_count"],
            page=page,
            page_size=page_size,
            has_next=result["pagination"]["has_next"]
        )
        
    except Exception as e:
        logger.error("Failed to list messages", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve messages"
        )


@router.get("/{message_id}", response_model=MessageResponse)
async def get_message(
    message_id: str,
    current_user: Dict = Depends(get_current_user_dependency())
):
    """Get specific message by ID."""
    
    try:
        # TODO: Query database for specific message
        # Placeholder implementation
        
        message = MessageResponse(
            id=message_id,
            content="Sample message content",
            message_type="telegram_out",
            channel_id="UC123456789",
            chat_id="@test_channel",
            timestamp=datetime.utcnow().isoformat(),
            user_id=None,
            thread_id="thread_001",
            metadata={"source": "youtube_summary"},
            formatting={"markdown": True},
            attachments=[]
        )
        
        logger.info("Retrieved message", message_id=message_id, user=current_user["username"])
        
        return message
        
    except Exception as e:
        logger.error("Failed to get message", message_id=message_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve message"
        )


@router.post("/send", response_model=Dict[str, str])
async def send_message(
    message_request: SendMessageRequest,
    current_user: Dict = Depends(get_current_user_dependency()),
    service: MessageMirrorService = Depends(get_message_mirror_service)
):
    """Send message through web interface to Telegram."""
    
    try:
        # Validate message content
        if not message_request.content.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message content cannot be empty"
            )
        
        # Send message via service
        result = await service.send_web_to_telegram(
            content=message_request.content,
            chat_id=message_request.chat_id,
            user_id=current_user["user_id"],
            formatting=message_request.formatting
        )
        
        logger.info("Sent message via web interface", 
                   chat_id=message_request.chat_id,
                   message_id=result["message_id"],
                   user=current_user["username"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to send message", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send message"
        )


@router.get("/threads", response_model=List[Dict[str, Any]])
async def list_threads(
    channel_id: Optional[str] = Query(None, description="Filter by channel ID"),
    chat_id: Optional[str] = Query(None, description="Filter by chat ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: Dict = Depends(get_current_user_dependency()),
    service: MessageMirrorService = Depends(get_message_mirror_service)
):
    """List message threads with filtering."""
    
    try:
        # Build query conditions
        conditions = []
        params = []
        
        if channel_id:
            conditions.append("channel_id = ?")
            params.append(channel_id)
        
        if chat_id:
            conditions.append("chat_id = ?")
            params.append(chat_id)
        
        if is_active is not None:
            conditions.append("is_active = ?")
            params.append(is_active)
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        
        # Get threads from database
        query = f"""
            SELECT * FROM message_threads
            {where_clause}
            ORDER BY last_message_at DESC
            LIMIT 100
        """
        
        threads = await service.db_manager.execute_query("messages", query, tuple(params))
        
        # Convert to response format
        thread_list = []
        for thread in threads:
            thread_list.append({
                "thread_id": thread["thread_id"],
                "title": thread["title"],
                "channel_id": thread["channel_id"],
                "chat_id": thread["chat_id"],
                "created_at": thread["created_at"],
                "last_message_at": thread["last_message_at"],
                "message_count": thread["message_count"],
                "participants": json.loads(thread.get("participants", "[]")),
                "is_active": bool(thread.get("is_active", True)),
                "is_archived": bool(thread.get("is_archived", False))
            })
        
        logger.info("Listed threads", count=len(thread_list), user=current_user["username"])
        
        return thread_list
        
    except Exception as e:
        logger.error("Failed to list threads", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve threads"
        )


@router.get("/threads/{thread_id}", response_model=MessageListResponse)
async def get_thread_messages(
    thread_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: Dict = Depends(get_current_user_dependency()),
    service: MessageMirrorService = Depends(get_message_mirror_service)
):
    """Get all messages in a specific thread."""
    
    try:
        # Get thread messages with pagination
        filters = {"thread_id": thread_id}
        pagination = {"page": page, "page_size": page_size}
        
        result = await service.get_message_history(filters, pagination)
        
        # Convert to response format
        messages = [
            MessageResponse(
                id=msg["id"],
                content=msg["content"],
                message_type=msg["message_type"],
                channel_id=msg["channel_id"],
                chat_id=msg["chat_id"],
                timestamp=msg["timestamp"],
                user_id=msg["user_id"],
                thread_id=msg["thread_id"],
                metadata=msg["metadata"],
                formatting=msg["formatting"],
                attachments=msg["attachments"]
            )
            for msg in result["messages"]
        ]
        
        logger.info("Retrieved thread messages", 
                   thread_id=thread_id, 
                   count=len(messages),
                   user=current_user["username"])
        
        return MessageListResponse(
            messages=messages,
            total_count=result["pagination"]["total_count"],
            page=page,
            page_size=page_size,
            has_next=result["pagination"]["has_next"]
        )
        
    except Exception as e:
        logger.error("Failed to get thread messages", thread_id=thread_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve thread messages"
        )


@router.post("/threads", response_model=Dict[str, str])
async def create_thread(
    title: str,
    channel_id: Optional[str] = None,
    chat_id: Optional[str] = None,
    current_user: Dict = Depends(get_current_user_dependency()),
    service: MessageMirrorService = Depends(get_message_mirror_service)
):
    """Create a new message thread."""
    
    try:
        thread_id = await service.create_thread(
            title=title,
            channel_id=channel_id,
            chat_id=chat_id
        )
        
        logger.info("Created thread", thread_id=thread_id, title=title, user=current_user["username"])
        
        return {
            "thread_id": thread_id,
            "title": title,
            "status": "created",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to create thread", title=title, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create thread"
        )


@router.get("/search", response_model=MessageListResponse)
async def search_messages(
    query: str = Query(..., description="Search query"),
    channel_id: Optional[str] = Query(None, description="Filter by channel"),
    message_type: Optional[str] = Query(None, description="Filter by message type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: Dict = Depends(get_current_user_dependency()),
    service: MessageMirrorService = Depends(get_message_mirror_service)
):
    """Full-text search across messages."""
    
    try:
        # Build filters
        filters = {}
        if channel_id:
            filters["channel_id"] = channel_id
        if message_type:
            filters["message_type"] = message_type
        
        # Execute search
        search_results = await service.search_messages(query, filters)
        
        # Apply pagination to search results
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_results = search_results[start_idx:end_idx]
        
        # Convert to response format
        messages = [
            MessageResponse(
                id=msg["id"],
                content=msg["content"],
                message_type=msg["message_type"],
                channel_id=msg["channel_id"],
                chat_id=msg["chat_id"],
                timestamp=msg["timestamp"],
                user_id=msg["user_id"],
                thread_id=msg["thread_id"],
                metadata=msg["metadata"],
                formatting=msg["formatting"],
                attachments=msg["attachments"]
            )
            for msg in paginated_results
        ]
        
        logger.info("Searched messages", 
                   query=query,
                   channel_id=channel_id,
                   results=len(search_results),
                   user=current_user["username"])
        
        return MessageListResponse(
            messages=messages,
            total_count=len(search_results),
            page=page,
            page_size=page_size,
            has_next=len(search_results) > page * page_size
        )
        
    except Exception as e:
        logger.error("Failed to search messages", query=query, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search messages"
        )


@router.get("/export", response_model=Dict[str, Any])
async def export_messages(
    format: str = Query("json", description="Export format (json, csv, txt)"),
    channel_id: Optional[str] = Query(None, description="Filter by channel ID"),
    chat_id: Optional[str] = Query(None, description="Filter by chat ID"),
    message_type: Optional[str] = Query(None, description="Filter by message type"),
    thread_id: Optional[str] = Query(None, description="Filter by thread ID"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    current_user: Dict = Depends(get_current_user_dependency()),
    service: MessageMirrorService = Depends(get_message_mirror_service)
):
    """Export messages in various formats."""
    
    try:
        # Validate format
        if format not in ["json", "csv", "txt"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid export format. Supported formats: json, csv, txt"
            )
        
        # Build filters
        filters = {}
        if channel_id:
            filters["channel_id"] = channel_id
        if chat_id:
            filters["chat_id"] = chat_id
        if message_type:
            filters["message_type"] = message_type
        if thread_id:
            filters["thread_id"] = thread_id
        if start_date:
            filters["start_date"] = start_date
        if end_date:
            filters["end_date"] = end_date
        
        # Get all messages (no pagination for export)
        result = await service.get_message_history(filters, {"page": 1, "page_size": 10000})
        messages = result["messages"]
        
        # Generate export data based on format
        if format == "json":
            export_data = {
                "export_info": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "user": current_user["username"],
                    "filters": filters,
                    "total_messages": len(messages)
                },
                "messages": messages
            }
            content_type = "application/json"
            
        elif format == "csv":
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                "id", "content", "message_type", "channel_id", "chat_id", 
                "timestamp", "user_id", "thread_id"
            ])
            
            # Write data
            for msg in messages:
                writer.writerow([
                    msg["id"], msg["content"], msg["message_type"],
                    msg["channel_id"], msg["chat_id"], msg["timestamp"],
                    msg["user_id"], msg["thread_id"]
                ])
            
            export_data = output.getvalue()
            content_type = "text/csv"
            
        elif format == "txt":
            lines = [f"Message Export - {datetime.utcnow().isoformat()}", "=" * 50, ""]
            
            for msg in messages:
                lines.append(f"ID: {msg['id']}")
                lines.append(f"Type: {msg['message_type']}")
                lines.append(f"Timestamp: {msg['timestamp']}")
                if msg['channel_id']:
                    lines.append(f"Channel: {msg['channel_id']}")
                if msg['chat_id']:
                    lines.append(f"Chat: {msg['chat_id']}")
                lines.append(f"Content: {msg['content']}")
                lines.append("-" * 30)
                lines.append("")
            
            export_data = "\n".join(lines)
            content_type = "text/plain"
        
        logger.info("Exported messages", 
                   format=format,
                   count=len(messages),
                   user=current_user["username"])
        
        return {
            "export_data": export_data,
            "content_type": content_type,
            "filename": f"messages_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{format}",
            "message_count": len(messages),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to export messages", format=format, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export messages"
        )


@router.get("/stats", response_model=Dict[str, Any])
async def get_message_stats(
    current_user: Dict = Depends(get_current_user_dependency()),
    service: MessageMirrorService = Depends(get_message_mirror_service)
):
    """Get message statistics and service status."""
    
    try:
        stats = await service.get_service_stats()
        
        logger.info("Retrieved message stats", user=current_user["username"])
        
        return stats
        
    except Exception as e:
        logger.error("Failed to get message stats", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve message statistics"
        )


# Service initialization function to be called by main app
def initialize_message_service(db_manager: DatabaseManager, ws_manager: WebSocketManager):
    """Initialize the message mirror service."""
    global message_mirror_service
    message_mirror_service = MessageMirrorService(db_manager, ws_manager)