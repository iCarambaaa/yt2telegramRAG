import sqlite3
from pathlib import Path
import logging
from typing import Optional, Dict, Any, List
import asyncio

from .exceptions import DatabaseError, ValidationError

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        if not self.db_path.parent.exists():
            try:
                self.db_path.parent.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise DatabaseError(f"Failed to create database directory {self.db_path.parent}: {e}")
        self._create_database()
    
    def _get_sync_connection(self) -> sqlite3.Connection:
        """Returns a synchronous SQLite connection."""
        conn = sqlite3.connect(
            self.db_path,
            timeout=30.0,
            isolation_level=None, # Autocommit mode
            check_same_thread=False # Allow cross-thread usage
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA temp_store=memory")
        return conn

    def _create_database(self):
        """Initialize database with proper connection management."""
        try:
            with self._get_sync_connection() as conn:
                self._create_tables(conn)
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to create database: {e}")
    
    def _create_tables(self, conn: sqlite3.Connection):
        """Create database tables if they don't exist."""
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS videos (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    channel_id TEXT,
                    published_at TEXT,
                    raw_subtitles TEXT,
                    cleaned_subtitles TEXT,
                    summary TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS channels (
                    id TEXT PRIMARY KEY,
                    last_check TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_videos_channel_id ON videos(channel_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_videos_published_at ON videos(published_at)
            ''')
            conn.commit()
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to create tables: {e}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._conn = await asyncio.to_thread(self._get_sync_connection)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._conn:
            await asyncio.to_thread(self._conn.close)
            self._conn = None

    async def get_last_check(self, channel_id: str) -> Optional[str]:
        """Get the last check timestamp for a channel."""
        def _get():
            cursor = self._conn.cursor()
            cursor.execute(
                "SELECT last_check FROM channels WHERE id = ?", 
                (channel_id,)
            )
            result = cursor.fetchone()
            return result[0] if result else None
        return await asyncio.to_thread(_get)
    
    async def update_last_check(self, channel_id: str, timestamp: str) -> None:
        """Update the last check timestamp for a channel."""
        def _update():
            cursor = self._conn.cursor()
            cursor.execute(
                """INSERT OR REPLACE INTO channels 
                   (id, last_check, updated_at) 
                   VALUES (?, ?, CURRENT_TIMESTAMP)""",
                (channel_id, timestamp)
            )
            self._conn.commit()
        await asyncio.to_thread(_update)
    
    async def add_video(self, video_data: Dict[str, Any]) -> None:
        """Add or update a video record."""
        def _add():
            cursor = self._conn.cursor()
            cursor.execute(
                """INSERT OR REPLACE INTO videos 
                   (id, title, channel_id, published_at, raw_subtitles, 
                    cleaned_subtitles, summary, updated_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                (
                    video_data['id'],
                    video_data['title'],
                    video_data['channel_id'],
                    video_data['published_at'],
                    video_data.get('raw_subtitles', ''),
                    video_data.get('cleaned_subtitles', ''),
                    video_data.get('summary', '')
                )
            )
            self._conn.commit()
        await asyncio.to_thread(_add)
    
    async def is_video_processed(self, video_id: str) -> bool:
        """Check if a video has already been processed."""
        def _check():
            cursor = self._conn.cursor()
            cursor.execute(
                "SELECT 1 FROM videos WHERE id = ?", 
                (video_id,)
            )
            return cursor.fetchone() is not None
        return await asyncio.to_thread(_check)
    
    async def get_video_by_id(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get a video record by ID."""
        def _get():
            cursor = self._conn.cursor()
            cursor.execute(
                "SELECT * FROM videos WHERE id = ?", 
                (video_id,)
            )
            result = cursor.fetchone()
            return dict(result) if result else None
        return await asyncio.to_thread(_get)
    
    async def get_videos_by_channel(self, channel_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get videos for a specific channel."""
        def _get_all():
            cursor = self._conn.cursor()
            cursor.execute(
                """SELECT * FROM videos 
                   WHERE channel_id = ? 
                   ORDER BY published_at DESC 
                   LIMIT ?""",
                (channel_id, limit)
            )
            return [dict(row) for row in cursor.fetchall()]
        return await asyncio.to_thread(_get_all)
    
    async def get_unprocessed_videos(self, channel_id: str) -> List[Dict[str, Any]]:
        """Get videos that haven't been fully processed (missing summary)."""
        def _get_unprocessed():
            cursor = self._conn.cursor()
            cursor.execute(
                """SELECT * FROM videos 
                   WHERE channel_id = ? 
                   AND (summary IS NULL OR summary = '')
                   ORDER BY published_at DESC""",
                (channel_id,)
            )
            return [dict(row) for row in cursor.fetchall()]
        return await asyncio.to_thread(_get_unprocessed)
    
    async def update_video_summary(self, video_id: str, summary: str) -> None:
        """Update the summary for a specific video."""
        def _update_summary():
            cursor = self._conn.cursor()
            cursor.execute(
                """UPDATE videos 
                   SET summary = ?, updated_at = CURRENT_TIMESTAMP 
                   WHERE id = ?""",
                (summary, video_id)
            )
            self._conn.commit()
        await asyncio.to_thread(_update_summary)
    
    async def get_channel_stats(self, channel_id: str) -> Dict[str, int]:
        """Get statistics for a channel."""
        def _get_stats():
            cursor = self._conn.cursor()
            cursor.execute(
                """SELECT 
                   COUNT(*) as total_videos,
                   COUNT(CASE WHEN summary IS NOT NULL AND summary != '' THEN 1 END) as processed_videos,
                   COUNT(CASE WHEN summary IS NULL OR summary = '' THEN 1 END) as unprocessed_videos
                   FROM videos WHERE channel_id = ?""",
                (channel_id,)
            )
            result = cursor.fetchone()
            return dict(result) if result else {
                'total_videos': 0,
                'processed_videos': 0,
                'unprocessed_videos': 0
            }
        return await asyncio.to_thread(_get_stats)
    
    async def cleanup_old_records(self, days_to_keep: int = 90) -> int:
        """Clean up old video records to manage database size."""
        def _cleanup():
            cursor = self._conn.cursor()
            cursor.execute(
                """DELETE FROM videos 
                   WHERE published_at < date('now', '-{} days')""".format(days_to_keep)
            )
            deleted_count = cursor.rowcount
            self._conn.commit()
            logger.info(f"Cleaned up {deleted_count} old video records")
            return deleted_count
        return await asyncio.to_thread(_cleanup)
    
    async def close(self) -> None:
        """Close all database connections (for cleanup)."""
        if self._conn:
            await asyncio.to_thread(self._conn.close)
            self._conn = None
        logger.info("Database connections closed")