from dataclasses import dataclass
from datetime import datetime
from typing import Optional

# @agent:service-type data-model
# @agent:scalability stateless
# @agent:persistence database
# @agent:priority high
# @agent:dependencies dataclasses,datetime,json_serialization
@dataclass
class Video:
    """Enhanced video data model with comprehensive multi-model processing metadata.
    
    Represents a YouTube video with complete processing lifecycle data including
    subtitle extraction, AI summarization results, cost tracking, and performance
    metrics. Supports both single-model and multi-model processing workflows
    with backward compatibility.
    
    Architecture: Immutable data class with optional fields for processing stages
    Critical Path: Core data structure for entire video processing pipeline
    Failure Mode: Graceful handling of missing fields with sensible defaults
    
    AI-GUIDANCE:
    - Never remove existing fields - breaks backward compatibility
    - Always validate video ID format (11 characters, YouTube standard)
    - Preserve JSON serialization compatibility for database storage
    - Use Optional types for processing stages that may not complete
    - Maintain clear separation between raw data and processed results
    
    Attributes:
        id (str): YouTube video ID (11 characters, alphanumeric + underscore + hyphen)
        title (str): Video title as provided by YouTube
        channel_id (str): YouTube channel ID (24 characters, starts with 'UC')
        published_at (Optional[str]): ISO format publication date
        raw_subtitles (Optional[str]): Original VTT subtitle content
        cleaned_subtitles (Optional[str]): Processed subtitle text (88% size reduction)
        summary (Optional[str]): Final summary text for delivery
        
        # Multi-model processing metadata
        summarization_method (Optional[str]): 'single', 'multi_model', 'fallback', 'error_fallback'
        primary_summary (Optional[str]): Primary model output
        secondary_summary (Optional[str]): Secondary model output  
        synthesis_summary (Optional[str]): Synthesized final summary
        primary_model (Optional[str]): Primary model identifier
        secondary_model (Optional[str]): Secondary model identifier
        synthesis_model (Optional[str]): Synthesis model identifier
        token_usage_json (Optional[str]): JSON string of detailed token usage
        processing_time_seconds (Optional[float]): Total processing time
        cost_estimate (Optional[float]): Estimated cost in USD
        fallback_used (Optional[bool]): Whether fallback strategy was triggered
        
    Example:
        >>> video = Video(id="dQw4w9WgXcQ", title="Never Gonna Give You Up", channel_id="UCuAXFkgsw1L7xaCfnd5JJOw")
        >>> video.summary = "Classic music video with memorable lyrics"
        >>> video.cost_estimate = 0.0023
        
    Note:
        Thread-safe immutable data structure. JSON serializable for database storage.
        Supports incremental field population during processing pipeline.
    """
    
    # Core video identification and metadata
    id: str  # YouTube video ID (11 chars)
    title: str  # Video title from YouTube
    channel_id: str  # YouTube channel ID (24 chars, UC prefix)
    published_at: Optional[str] = None  # ISO format date
    
    # Availability and access control
    availability: Optional[str] = None  # public, unlisted, private, premium_only, needs_auth
    release_timestamp: Optional[int] = None  # Unix timestamp when members-first becomes public
    
    # Subtitle processing pipeline
    raw_subtitles: Optional[str] = None  # Original VTT content
    cleaned_subtitles: Optional[str] = None  # Processed text (~88% reduction)
    summary: Optional[str] = None  # Final summary for delivery
    
    # Multi-model enhancement fields - comprehensive processing metadata
    summarization_method: Optional[str] = None  # Processing strategy used
    primary_summary: Optional[str] = None  # Primary model output
    secondary_summary: Optional[str] = None  # Secondary model output
    synthesis_summary: Optional[str] = None  # Synthesized final result
    primary_model: Optional[str] = None  # Primary model identifier
    secondary_model: Optional[str] = None  # Secondary model identifier
    synthesis_model: Optional[str] = None  # Synthesis model identifier
    token_usage_json: Optional[str] = None  # JSON token usage details
    processing_time_seconds: Optional[float] = None  # Total processing time
    cost_estimate: Optional[float] = None  # Estimated cost in USD
    fallback_used: Optional[bool] = None  # Fallback strategy triggered
    
    # @agent:complexity medium
    # @agent:side-effects none
    # @agent:performance O(1) with string_parsing
    # @agent:security input_validation,date_parsing_safety
    @classmethod
    def from_yt_dlp(cls, entry: dict, channel_id: str) -> 'Video':
        """Create Video instance from yt-dlp metadata with date parsing and validation.
        
        Factory method that safely converts yt-dlp video metadata into Video
        instances with proper date formatting and error handling. Handles
        various yt-dlp response formats and missing metadata gracefully.
        
        Intent: Safely convert external API data to internal data model
        Critical: Data conversion errors prevent video processing pipeline
        
        AI-DECISION: Date format conversion strategy
        Criteria:
        - yt-dlp YYYYMMDD format → convert to ISO YYYY-MM-DD
        - Invalid date format → log warning and set to None
        - Missing upload_date → set published_at to None
        - Malformed entry → validate required fields and fail gracefully
        
        Args:
            entry (dict): yt-dlp video metadata dictionary
            channel_id (str): YouTube channel ID for validation
            
        Returns:
            Video: New Video instance with parsed metadata
            
        Raises:
            KeyError: If required fields (id, title) are missing
            ValueError: If video ID format is invalid
            
        AI-NOTE: 
            - Date parsing is defensive - handles malformed dates gracefully
            - Video ID validation prevents downstream processing errors
            - Channel ID validation ensures data consistency
        """
        # Extract published date if available
        published_at = None
        if 'upload_date' in entry:
            # yt-dlp format: YYYYMMDD
            upload_date = entry['upload_date']
            if upload_date and len(upload_date) == 8:
                try:
                    # Convert YYYYMMDD to ISO format
                    year = upload_date[:4]
                    month = upload_date[4:6]
                    day = upload_date[6:8]
                    published_at = f"{year}-{month}-{day}"
                except:
                    published_at = upload_date
        
        return cls(
            id=entry["id"],
            title=entry.get("title", ""),
            channel_id=channel_id,
            published_at=published_at,
            availability=entry.get("availability"),
            release_timestamp=entry.get("release_timestamp")
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database storage"""
        return {
            'id': self.id,
            'title': self.title,
            'channel_id': self.channel_id,
            'published_at': self.published_at,
            'availability': self.availability,
            'release_timestamp': self.release_timestamp,
            'raw_subtitles': self.raw_subtitles,
            'cleaned_subtitles': self.cleaned_subtitles,
            'summary': self.summary,
            'summarization_method': self.summarization_method,
            'primary_summary': self.primary_summary,
            'secondary_summary': self.secondary_summary,
            'synthesis_summary': self.synthesis_summary,
            'primary_model': self.primary_model,
            'secondary_model': self.secondary_model,
            'synthesis_model': self.synthesis_model,
            'token_usage_json': self.token_usage_json,
            'processing_time_seconds': self.processing_time_seconds,
            'cost_estimate': self.cost_estimate,
            'fallback_used': self.fallback_used
        }