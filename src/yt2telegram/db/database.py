#!/usr/bin/env python3
"""
Database operations for the YouTube2Telegram RAG system.
Handles SQLite database creation, queries, and data management.
"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages all database operations for the YouTube2Telegram system."""
    
    def __init__(self, db_path: str = "youtube_telegram.db"):
        """
        Initialize the database manager.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path)
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create processed_videos table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS processed_videos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        video_id TEXT UNIQUE NOT NULL,
                        channel_id TEXT NOT NULL,
                        title TEXT NOT NULL,
                        description TEXT,
                        published_at TEXT,
                        processed_at TEXT NOT NULL,
                        summary TEXT,
                        telegram_message_id TEXT,
                        status TEXT DEFAULT 'processed',
                        metadata TEXT
                    )
                ''')
                
                # Create channels table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS channels (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        channel_id TEXT UNIQUE NOT NULL,
                        channel_name TEXT NOT NULL,
                        last_check TEXT,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TEXT NOT NULL
                    )
                ''')
                
                # Create subtitles table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS subtitles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        video_id TEXT NOT NULL,
                        subtitle_text TEXT NOT NULL,
                        language TEXT DEFAULT 'en',
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (video_id) REFERENCES processed_videos (video_id)
                    )
                ''')
                
                # Create embeddings table for RAG
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS embeddings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        video_id TEXT NOT NULL,
                        chunk_index INTEGER NOT NULL,
                        chunk_text TEXT NOT NULL,
                        embedding BLOB,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (video_id) REFERENCES processed_videos (video_id)
                    )
                ''')
                
                # Create indexes for better performance
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_processed_videos_channel 
                    ON processed_videos(channel_id)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_processed_videos_date 
                    ON processed_videos(published_at)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_subtitles_video 
                    ON subtitles(video_id)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_embeddings_video 
                    ON embeddings(video_id)
                ''')
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except sqlite3.Error as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def add_video(self, video_data: Dict) -> bool:
        """
        Add a processed video to the database.
        
        Args:
            video_data: Dictionary containing video information
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO processed_videos 
                    (video_id, channel_id, title, description, published_at, 
                     processed_at, summary, telegram_message_id, status, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    video_data['video_id'],
                    video_data['channel_id'],
                    video_data['title'],
                    video_data.get('description', ''),
                    video_data['published_at'],
                    datetime.now().isoformat(),
                    video_data.get('summary', ''),
                    video_data.get('telegram_message_id', ''),
                    video_data.get('status', 'processed'),
                    json.dumps(video_data.get('metadata', {}))
                ))
                
                conn.commit()
                logger.info(f"Added video {video_data['video_id']} to database")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Error adding video: {e}")
            return False
    
    def add_channel(self, channel_id: str, channel_name: str) -> bool:
        """
        Add a YouTube channel to monitor.
        
        Args:
            channel_id: YouTube channel ID
            channel_name: Human-readable channel name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR IGNORE INTO channels 
                    (channel_id, channel_name, created_at)
                    VALUES (?, ?, ?)
                ''', (channel_id, channel_name, datetime.now().isoformat()))
                
                conn.commit()
                logger.info(f"Added channel {channel_name} ({channel_id})")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Error adding channel: {e}")
            return False
    
    def get_channel_videos(self, channel_id: str, limit: int = 50) -> List[Dict]:
        """
        Get all processed videos for a specific channel.
        
        Args:
            channel_id: YouTube channel ID
            limit: Maximum number of videos to return
            
        Returns:
            List of video dictionaries
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM processed_videos 
                    WHERE channel_id = ? 
                    ORDER BY published_at DESC 
                    LIMIT ?
                ''', (channel_id, limit))
                
                rows = cursor.fetchall()
                videos = []
                
                for row in rows:
                    video = dict(row)
                    if video['metadata']:
                        video['metadata'] = json.loads(video['metadata'])
                    videos.append(video)
                
                return videos
                
        except sqlite3.Error as e:
            logger.error(f"Error getting channel videos: {e}")
            return []
    
    def get_video_by_id(self, video_id: str) -> Optional[Dict]:
        """
        Get a specific video by its ID.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Video dictionary or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM processed_videos 
                    WHERE video_id = ?
                ''', (video_id,))
                
                row = cursor.fetchone()
                if row:
                    video = dict(row)
                    if video['metadata']:
                        video['metadata'] = json.loads(video['metadata'])
                    return video
                
                return None
                
        except sqlite3.Error as e:
            logger.error(f"Error getting video: {e}")
            return None
    
    def add_subtitle(self, video_id: str, subtitle_text: str, language: str = 'en') -> bool:
        """
        Add subtitle text for a video.
        
        Args:
            video_id: YouTube video ID
            subtitle_text: The subtitle content
            language: Language code (default: 'en')
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO subtitles 
                    (video_id, subtitle_text, language, created_at)
                    VALUES (?, ?, ?, ?)
                ''', (video_id, subtitle_text, language, datetime.now().isoformat()))
                
                conn.commit()
                logger.info(f"Added subtitles for video {video_id}")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Error adding subtitle: {e}")
            return False
    
    def get_subtitles(self, video_id: str) -> List[Dict]:
        """
        Get all subtitles for a video.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            List of subtitle dictionaries
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM subtitles 
                    WHERE video_id = ? 
                    ORDER BY created_at DESC
                ''', (video_id,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except sqlite3.Error as e:
            logger.error(f"Error getting subtitles: {e}")
            return []
    
    def search_videos(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search for videos by title or description.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            
        Returns:
            List of matching video dictionaries
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM processed_videos 
                    WHERE title LIKE ? OR description LIKE ? 
                    ORDER BY published_at DESC 
                    LIMIT ?
                ''', (f'%{query}%', f'%{query}%', limit))
                
                rows = cursor.fetchall()
                videos = []
                
                for row in rows:
                    video = dict(row)
                    if video['metadata']:
                        video['metadata'] = json.loads(video['metadata'])
                    videos.append(video)
                
                return videos
                
        except sqlite3.Error as e:
            logger.error(f"Error searching videos: {e}")
            return []
    
    def get_active_channels(self) -> List[Dict]:
        """
        Get all active channels being monitored.
        
        Returns:
            List of channel dictionaries
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM channels 
                    WHERE is_active = 1 
                    ORDER BY channel_name
                ''')
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except sqlite3.Error as e:
            logger.error(f"Error getting active channels: {e}")
            return []
    
    def update_channel_last_check(self, channel_id: str) -> bool:
        """
        Update the last check timestamp for a channel.
        
        Args:
            channel_id: YouTube channel ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE channels 
                    SET last_check = ? 
                    WHERE channel_id = ?
                ''', (datetime.now().isoformat(), channel_id))
                
                conn.commit()
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Error updating channel last check: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """
        Get database statistics.
        
        Returns:
            Dictionary with various statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Count videos
                cursor.execute('SELECT COUNT(*) FROM processed_videos')
                video_count = cursor.fetchone()[0]
                
                # Count channels
                cursor.execute('SELECT COUNT(*) FROM channels WHERE is_active = 1')
                channel_count = cursor.fetchone()[0]
                
                # Count subtitles
                cursor.execute('SELECT COUNT(*) FROM subtitles')
                subtitle_count = cursor.fetchone()[0]
                
                # Latest video
                cursor.execute('''
                    SELECT title, published_at 
                    FROM processed_videos 
                    ORDER BY published_at DESC 
                    LIMIT 1
                ''')
                latest = cursor.fetchone()
                
                return {
                    'total_videos': video_count,
                    'active_channels': channel_count,
                    'total_subtitles': subtitle_count,
                    'latest_video': {
                        'title': latest[0] if latest else None,
                        'published_at': latest[1] if latest else None
                    } if latest else None
                }
                
        except sqlite3.Error as e:
            logger.error(f"Error getting stats: {e}")
            return {}
    
    def execute_query(self, query: str, params: Tuple = ()) -> List[Dict]:
        """
        Execute a raw SQL query and return results.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of result dictionaries
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                
                if query.strip().upper().startswith('SELECT'):
                    rows = cursor.fetchall()
                    return [dict(row) for row in rows]
                return []
                
        except sqlite3.Error as e:
            logger.error(f"Error executing query: {e}")
            return []

    def close(self):
        """Close database connection (not needed with context managers)."""
        pass