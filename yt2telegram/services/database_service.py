import sqlite3
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from ..models.video import Video
from ..utils.logging_config import LoggerFactory

logger = LoggerFactory.create_logger(__name__)

class DatabaseService:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._create_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with optimized settings"""
        conn = sqlite3.connect(
            self.db_path,
            timeout=30.0,
            isolation_level=None,  # Autocommit mode
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _create_database(self):
        """Initialize database tables"""
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS videos (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    channel_id TEXT NOT NULL,
                    raw_subtitles TEXT,
                    cleaned_subtitles TEXT,
                    summary TEXT,
                    processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS channel_status (
                    channel_id TEXT PRIMARY KEY,
                    last_check TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for better performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_videos_channel_id ON videos(channel_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_videos_processed_at ON videos(processed_at)')

    def is_video_processed(self, video_id: str) -> bool:
        """Check if video has already been processed"""
        with self._get_connection() as conn:
            cursor = conn.execute('SELECT 1 FROM videos WHERE id = ?', (video_id,))
            return cursor.fetchone() is not None

    def add_video(self, video: Video):
        """Add video to database"""
        with self._get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO videos 
                (id, title, channel_id, raw_subtitles, cleaned_subtitles, summary)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                video.id,
                video.title,
                video.channel_id,
                video.raw_subtitles,
                video.cleaned_subtitles,
                video.summary
            ))
        logger.info("Added video to database", video_id=video.id)

    def get_last_check(self, channel_id: str) -> Optional[str]:
        """Get last check timestamp for channel"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                'SELECT last_check FROM channel_status WHERE channel_id = ?',
                (channel_id,)
            )
            row = cursor.fetchone()
            return row['last_check'] if row else None

    def update_last_check(self, channel_id: str, timestamp: str):
        """Update last check timestamp for channel"""
        with self._get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO channel_status (channel_id, last_check)
                VALUES (?, ?)
            ''', (channel_id, timestamp))
        logger.info("Updated last check for channel", channel_id=channel_id)

    def get_recent_videos(self, channel_id: str, limit: int = 10) -> List[Video]:
        """Get recent videos for a channel"""
        with self._get_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM videos 
                WHERE channel_id = ? 
                ORDER BY processed_at DESC 
                LIMIT ?
            ''', (channel_id, limit))
            
            videos = []
            for row in cursor.fetchall():
                video = Video(
                    id=row['id'],
                    title=row['title'],
                    channel_id=row['channel_id'],
                    raw_subtitles=row['raw_subtitles'],
                    cleaned_subtitles=row['cleaned_subtitles'],
                    summary=row['summary']
                )
                videos.append(video)
            
            return videos