"""Database query engine for Q&A bot."""
import sqlite3
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

class DatabaseQuery:
    """Query engine for channel databases."""
    
    def __init__(self, db_path: str):
        """Initialize database connection."""
        self.db_path = db_path
    
    def search_content(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for content matching query in summaries and subtitles."""
        results = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Search in video summaries
                cursor = conn.execute("""
                    SELECT video_id, title, summary, upload_date, url
                    FROM videos
                    WHERE summary LIKE ? OR title LIKE ?
                    ORDER BY upload_date DESC
                    LIMIT ?
                """, (f'%{query}%', f'%{query}%', limit))
                
                for row in cursor.fetchall():
                    results.append({
                        'type': 'summary',
                        'video_id': row['video_id'],
                        'title': row['title'],
                        'content': row['summary'],
                        'upload_date': row['upload_date'],
                        'url': row['url']
                    })
                
                # Search in cleaned subtitles
                cursor = conn.execute("""
                    SELECT v.video_id, v.title, s.content, s.start_time, v.upload_date, v.url
                    FROM videos v
                    JOIN subtitles s ON v.video_id = s.video_id
                    WHERE s.content LIKE ?
                    ORDER BY v.upload_date DESC, s.start_time ASC
                    LIMIT ?
                """, (f'%{query}%', limit))
                
                for row in cursor.fetchall():
                    results.append({
                        'type': 'subtitle',
                        'video_id': row['video_id'],
                        'title': row['title'],
                        'content': row['content'],
                        'timestamp': row['start_time'],
                        'upload_date': row['upload_date'],
                        'url': row['url']
                    })
                
        except sqlite3.Error as e:
            print(f"Database error: {e}")
        
        return results
    
    def get_latest_videos(self, limit: int = 3) -> List[Dict[str, Any]]:
        """Get latest video summaries."""
        results = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                cursor = conn.execute("""
                    SELECT video_id, title, summary, upload_date, url
                    FROM videos
                    ORDER BY upload_date DESC
                    LIMIT ?
                """, (limit,))
                
                for row in cursor.fetchall():
                    results.append({
                        'video_id': row['video_id'],
                        'title': row['title'],
                        'summary': row['summary'],
                        'upload_date': row['upload_date'],
                        'url': row['url']
                    })
                
        except sqlite3.Error as e:
            print(f"Database error: {e}")
        
        return results
    
    def get_video_by_id(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get specific video details."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                cursor = conn.execute("""
                    SELECT video_id, title, summary, upload_date, url
                    FROM videos
                    WHERE video_id = ?
                """, (video_id,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'video_id': row['video_id'],
                        'title': row['title'],
                        'summary': row['summary'],
                        'upload_date': row['upload_date'],
                        'url': row['url']
                    }
                
        except sqlite3.Error as e:
            print(f"Database error: {e}")
        
        return None