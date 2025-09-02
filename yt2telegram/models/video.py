from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Video:
    id: str
    title: str
    channel_id: str
    published_at: Optional[str] = None
    raw_subtitles: Optional[str] = None
    cleaned_subtitles: Optional[str] = None
    summary: Optional[str] = None
    
    # Multi-model enhancement fields
    summarization_method: Optional[str] = None
    primary_summary: Optional[str] = None
    secondary_summary: Optional[str] = None
    synthesis_summary: Optional[str] = None
    primary_model: Optional[str] = None
    secondary_model: Optional[str] = None
    synthesis_model: Optional[str] = None
    token_usage_json: Optional[str] = None
    processing_time_seconds: Optional[float] = None
    cost_estimate: Optional[float] = None
    fallback_used: Optional[bool] = None
    
    @classmethod
    def from_yt_dlp(cls, entry: dict, channel_id: str) -> 'Video':
        """Create Video from yt-dlp entry"""
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
            published_at=published_at
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database storage"""
        return {
            'id': self.id,
            'title': self.title,
            'channel_id': self.channel_id,
            'published_at': self.published_at,
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