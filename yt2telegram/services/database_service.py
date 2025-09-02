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
        """Initialize database tables with enhanced multi-model schema"""
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS videos (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    channel_id TEXT NOT NULL,
                    published_at TEXT,
                    raw_subtitles TEXT,
                    cleaned_subtitles TEXT,
                    summary TEXT,
                    processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    
                    -- Multi-model enhancement fields
                    summarization_method TEXT DEFAULT 'single',
                    primary_summary TEXT,
                    secondary_summary TEXT,
                    synthesis_summary TEXT,
                    primary_model TEXT,
                    secondary_model TEXT,
                    synthesis_model TEXT,
                    token_usage_json TEXT,
                    processing_time_seconds REAL,
                    cost_estimate REAL,
                    fallback_used INTEGER DEFAULT 0
                )
            ''')
            
            # Migrate existing databases to enhanced schema
            self._migrate_to_enhanced_schema(conn)
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS channel_status (
                    channel_id TEXT PRIMARY KEY,
                    last_check TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            ''')
    
    def _migrate_to_enhanced_schema(self, conn):
        """Migrate existing database to enhanced multi-model schema"""
        # Get current columns
        cursor = conn.execute("PRAGMA table_info(videos)")
        existing_columns = {col[1] for col in cursor.fetchall()}
        
        # Add missing columns for multi-model support
        new_columns = [
            ('published_at', 'TEXT'),
            ('summarization_method', 'TEXT DEFAULT "single"'),
            ('primary_summary', 'TEXT'),
            ('secondary_summary', 'TEXT'),
            ('synthesis_summary', 'TEXT'),
            ('primary_model', 'TEXT'),
            ('secondary_model', 'TEXT'),
            ('synthesis_model', 'TEXT'),
            ('token_usage_json', 'TEXT'),
            ('processing_time_seconds', 'REAL'),
            ('cost_estimate', 'REAL'),
            ('fallback_used', 'INTEGER DEFAULT 0')
        ]
        
        for column_name, column_type in new_columns:
            if column_name not in existing_columns:
                try:
                    conn.execute(f'ALTER TABLE videos ADD COLUMN {column_name} {column_type}')
                    logger.info(f"Added column {column_name} to videos table")
                except sqlite3.OperationalError as e:
                    logger.warning(f"Could not add column {column_name}: {e}")
            
            # Create indexes for better performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_videos_channel_id ON videos(channel_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_videos_processed_at ON videos(processed_at)')

    def is_video_processed(self, video_id: str) -> bool:
        """Check if video has already been processed"""
        with self._get_connection() as conn:
            cursor = conn.execute('SELECT 1 FROM videos WHERE id = ?', (video_id,))
            return cursor.fetchone() is not None

    def add_video(self, video: Video):
        """Add video to database with enhanced multi-model support"""
        with self._get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO videos 
                (id, title, channel_id, published_at, raw_subtitles, cleaned_subtitles, summary,
                 summarization_method, primary_summary, secondary_summary, synthesis_summary,
                 primary_model, secondary_model, synthesis_model, token_usage_json,
                 processing_time_seconds, cost_estimate, fallback_used)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                video.id,
                video.title,
                video.channel_id,
                video.published_at,
                video.raw_subtitles,
                video.cleaned_subtitles,
                video.summary,
                video.summarization_method,
                video.primary_summary,
                video.secondary_summary,
                video.synthesis_summary,
                video.primary_model,
                video.secondary_model,
                video.synthesis_model,
                video.token_usage_json,
                video.processing_time_seconds,
                video.cost_estimate,
                1 if video.fallback_used else 0 if video.fallback_used is not None else None
            ))
        logger.info("Added video to database", video_id=video.id, published_at=video.published_at)

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