from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Video:
    id: str
    title: str
    channel_id: str
    raw_subtitles: Optional[str] = None
    cleaned_subtitles: Optional[str] = None
    summary: Optional[str] = None
    
    @classmethod
    def from_yt_dlp(cls, entry: dict, channel_id: str) -> 'Video':
        """Create Video from yt-dlp entry"""
        return cls(
            id=entry["id"],
            title=entry.get("title", ""),
            channel_id=channel_id
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database storage"""
        return {
            'id': self.id,
            'title': self.title,
            'channel_id': self.channel_id,
            'raw_subtitles': self.raw_subtitles,
            'cleaned_subtitles': self.cleaned_subtitles,
            'summary': self.summary
        }