"""
Data models for message mirror functionality.

CRITICAL: Core data structures for message handling
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
from enum import Enum


class MessageType(str, Enum):
    """Enumeration of message types."""
    TELEGRAM_OUT = "telegram_out"
    TELEGRAM_IN = "telegram_in"
    WEB_OUT = "web_out"
    QNA_QUESTION = "qna_question"
    QNA_ANSWER = "qna_answer"


class MessageStatus(str, Enum):
    """Message processing status."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    QUEUED = "queued"


class MessageAttachment(BaseModel):
    """Message attachment model."""
    type: str = Field(..., description="Attachment type (image, video, document, etc.)")
    url: Optional[str] = Field(None, description="Attachment URL")
    filename: Optional[str] = Field(None, description="Original filename")
    size: Optional[int] = Field(None, description="File size in bytes")
    mime_type: Optional[str] = Field(None, description="MIME type")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class MessageFormatting(BaseModel):
    """Message formatting options."""
    markdown: bool = Field(default=False, description="Use Markdown formatting")
    html: bool = Field(default=False, description="Use HTML formatting")
    entities: List[Dict[str, Any]] = Field(default_factory=list, description="Text entities")
    parse_mode: Optional[str] = Field(None, description="Telegram parse mode")


class MessageMetadata(BaseModel):
    """Message metadata."""
    source: Optional[str] = Field(None, description="Message source system")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")
    cost: Optional[float] = Field(None, description="Processing cost in USD")
    model_used: Optional[str] = Field(None, description="AI model used for processing")
    retry_count: int = Field(default=0, description="Number of retry attempts")
    original_message_id: Optional[str] = Field(None, description="Original message ID if forwarded")
    tags: List[str] = Field(default_factory=list, description="Message tags")


class UnifiedMessageModel(BaseModel):
    """Unified message model for all interfaces."""
    id: str = Field(..., description="Unique message identifier")
    content: str = Field(..., description="Message content")
    message_type: MessageType = Field(..., description="Type of message")
    status: MessageStatus = Field(default=MessageStatus.PENDING, description="Message status")
    
    # Identifiers
    channel_id: Optional[str] = Field(None, description="YouTube channel ID")
    chat_id: Optional[str] = Field(None, description="Telegram chat ID")
    user_id: Optional[str] = Field(None, description="User ID who sent the message")
    thread_id: Optional[str] = Field(None, description="Conversation thread ID")
    
    # Timestamps
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")
    sent_at: Optional[datetime] = Field(None, description="When message was sent")
    delivered_at: Optional[datetime] = Field(None, description="When message was delivered")
    
    # Content structure
    metadata: MessageMetadata = Field(default_factory=MessageMetadata, description="Message metadata")
    formatting: MessageFormatting = Field(default_factory=MessageFormatting, description="Formatting options")
    attachments: List[MessageAttachment] = Field(default_factory=list, description="Message attachments")
    
    # Search and indexing
    search_content: Optional[str] = Field(None, description="Processed content for search")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MessageThreadModel(BaseModel):
    """Message thread for conversation grouping."""
    thread_id: str = Field(..., description="Unique thread identifier")
    title: str = Field(..., description="Thread title")
    
    # Context
    channel_id: Optional[str] = Field(None, description="Associated channel ID")
    chat_id: Optional[str] = Field(None, description="Associated chat ID")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Thread creation time")
    last_message_at: datetime = Field(default_factory=datetime.utcnow, description="Last message time")
    
    # Statistics
    message_count: int = Field(default=0, description="Number of messages in thread")
    participants: List[str] = Field(default_factory=list, description="Thread participants")
    
    # Status
    is_active: bool = Field(default=True, description="Whether thread is active")
    is_archived: bool = Field(default=False, description="Whether thread is archived")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MessageFilter(BaseModel):
    """Message filtering options."""
    channel_id: Optional[str] = Field(None, description="Filter by channel ID")
    chat_id: Optional[str] = Field(None, description="Filter by chat ID")
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    thread_id: Optional[str] = Field(None, description="Filter by thread ID")
    message_type: Optional[MessageType] = Field(None, description="Filter by message type")
    status: Optional[MessageStatus] = Field(None, description="Filter by status")
    
    # Date range
    start_date: Optional[datetime] = Field(None, description="Start date for filtering")
    end_date: Optional[datetime] = Field(None, description="End date for filtering")
    
    # Content filtering
    search_query: Optional[str] = Field(None, description="Search query for content")
    has_attachments: Optional[bool] = Field(None, description="Filter messages with attachments")
    
    # Tags
    tags: List[str] = Field(default_factory=list, description="Filter by tags")


class MessagePagination(BaseModel):
    """Pagination options for message queries."""
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=50, ge=1, le=100, description="Items per page")
    sort_by: str = Field(default="timestamp", description="Sort field")
    sort_order: Literal["asc", "desc"] = Field(default="desc", description="Sort order")


class MessageHistoryResponse(BaseModel):
    """Response model for message history queries."""
    messages: List[UnifiedMessageModel] = Field(..., description="List of messages")
    pagination: Dict[str, Any] = Field(..., description="Pagination information")
    filters_applied: MessageFilter = Field(..., description="Applied filters")
    total_count: int = Field(..., description="Total number of messages")


class MessageSearchResponse(BaseModel):
    """Response model for message search queries."""
    messages: List[UnifiedMessageModel] = Field(..., description="Search results")
    query: str = Field(..., description="Search query")
    total_results: int = Field(..., description="Total number of results")
    search_time_ms: float = Field(..., description="Search execution time")


class SendMessageRequest(BaseModel):
    """Request model for sending messages."""
    content: str = Field(..., min_length=1, max_length=4096, description="Message content")
    chat_id: str = Field(..., description="Target chat ID")
    message_type: MessageType = Field(default=MessageType.WEB_OUT, description="Message type")
    
    # Optional fields
    thread_id: Optional[str] = Field(None, description="Thread ID for conversation")
    formatting: MessageFormatting = Field(default_factory=MessageFormatting, description="Formatting options")
    attachments: List[MessageAttachment] = Field(default_factory=list, description="Message attachments")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    # Scheduling
    schedule_at: Optional[datetime] = Field(None, description="Schedule message for later")
    
    class Config:
        use_enum_values = True


class SendMessageResponse(BaseModel):
    """Response model for message sending."""
    message_id: str = Field(..., description="Generated message ID")
    status: MessageStatus = Field(..., description="Message status")
    timestamp: datetime = Field(..., description="Processing timestamp")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MessageStatsResponse(BaseModel):
    """Response model for message statistics."""
    total_messages: int = Field(..., description="Total number of messages")
    message_types: Dict[str, int] = Field(..., description="Count by message type")
    recent_activity: List[Dict[str, Any]] = Field(..., description="Recent activity data")
    queued_messages: int = Field(..., description="Number of queued messages")
    
    # Performance metrics
    average_processing_time: Optional[float] = Field(None, description="Average processing time")
    success_rate: Optional[float] = Field(None, description="Message success rate")
    
    # Storage metrics
    total_storage_mb: Optional[float] = Field(None, description="Total storage used in MB")
    attachment_count: Optional[int] = Field(None, description="Total number of attachments")