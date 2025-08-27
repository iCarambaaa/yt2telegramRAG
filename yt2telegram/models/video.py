from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .multi_model import TokenUsage, FallbackStrategy

@dataclass
class Video:
    # Existing fields (preserved for backward compatibility)
    id: str
    title: str
    channel_id: str
    raw_subtitles: Optional[str] = None
    cleaned_subtitles: Optional[str] = None
    summary: Optional[str] = None  # Final summary (backward compatibility)
    
    # Multi-model specific fields
    primary_summary: Optional[str] = None
    secondary_summary: Optional[str] = None
    synthesis_summary: Optional[str] = None
    
    # Processing metadata fields
    summarization_method: str = 'single'  # 'single' or 'multi-model'
    primary_model: Optional[str] = None
    secondary_model: Optional[str] = None
    synthesis_model: Optional[str] = None
    processing_time_seconds: Optional[float] = None
    
    # Fallback tracking fields
    fallback_used: bool = False
    fallback_strategy: Optional[str] = None  # Store as string for database compatibility
    error_details: Optional[str] = None
    
    # Token usage field
    token_usage: Optional[TokenUsage] = None
    
    @classmethod
    def from_yt_dlp(cls, entry: dict, channel_id: str) -> 'Video':
        """Create Video from yt-dlp entry"""
        return cls(
            id=entry["id"],
            title=entry.get("title", ""),
            channel_id=channel_id
        )
    
    def get_final_summary(self) -> Optional[str]:
        """Get the final summary, prioritizing synthesis over primary over summary"""
        return self.synthesis_summary or self.primary_summary or self.summary
    
    def is_multi_model(self) -> bool:
        """Check if this video was processed with multi-model approach"""
        return self.summarization_method == 'multi-model'
    
    def get_token_usage(self) -> Optional[TokenUsage]:
        """Get structured token usage data"""
        return self.token_usage
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database storage"""
        return {
            'id': self.id,
            'title': self.title,
            'channel_id': self.channel_id,
            'raw_subtitles': self.raw_subtitles,
            'cleaned_subtitles': self.cleaned_subtitles,
            'summary': self.summary,
            'primary_summary': self.primary_summary,
            'secondary_summary': self.secondary_summary,
            'synthesis_summary': self.synthesis_summary,
            'summarization_method': self.summarization_method,
            'primary_model': self.primary_model,
            'secondary_model': self.secondary_model,
            'synthesis_model': self.synthesis_model,
            'processing_time_seconds': self.processing_time_seconds,
            'fallback_used': self.fallback_used,
            'fallback_strategy': self.fallback_strategy,
            'error_details': self.error_details,
            'token_usage': self.token_usage
        }