"""
Channel Database Service for connecting to existing YouTube channel databases.

CRITICAL: Bridge between GUI and existing channel data
DEPENDENCIES: Existing channel SQLite databases
"""

import sqlite3
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from utils.logging_config import setup_logging

logger = setup_logging(__name__)


class ChannelDatabaseService:
    """Service for accessing existing YouTube channel databases."""
    
    def __init__(self):
        import os
        # Get the project root directory (go up from gui/services/ to project root)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        gui_dir = os.path.dirname(current_dir)  # gui directory
        project_root = os.path.dirname(gui_dir)  # project root
        
        self.downloads_dir = os.path.join(project_root, "yt2telegram", "downloads")
        self.channel_configs_dir = os.path.join(project_root, "yt2telegram", "channels")
        
        logger.info(f"Database service initialized - Downloads dir: {self.downloads_dir}")
    
    def get_available_channels(self) -> List[Dict[str, Any]]:
        """Get list of available channels with metadata."""
        channels = []
        
        try:
            if not os.path.exists(self.downloads_dir):
                logger.warning(f"Downloads directory not found: {self.downloads_dir}")
                return channels
            
            # Scan for database files
            for file in os.listdir(self.downloads_dir):
                if file.endswith('.db'):
                    channel_name = file[:-3]  # Remove .db extension
                    db_path = os.path.join(self.downloads_dir, file)
                    
                    # Get channel metadata
                    metadata = self._get_channel_metadata(channel_name, db_path)
                    if metadata:
                        channels.append(metadata)
            
            logger.info(f"Found {len(channels)} channel databases")
            return channels
            
        except Exception as e:
            logger.error(f"Failed to get available channels: {str(e)}")
            return []
    
    def _get_channel_metadata(self, channel_name: str, db_path: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific channel."""
        try:
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Get basic channel info
                cursor = conn.execute("""
                    SELECT COUNT(*) as video_count,
                           MIN(published_at) as first_video,
                           MAX(published_at) as latest_video
                    FROM videos
                """)
                stats = cursor.fetchone()
                
                # Get a sample video for channel info
                cursor = conn.execute("""
                    SELECT title, channel_name, url
                    FROM videos
                    ORDER BY published_at DESC
                    LIMIT 1
                """)
                sample_video = cursor.fetchone()
                
                # Check if subtitles table exists
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='subtitles'
                """)
                has_subtitles = cursor.fetchone() is not None
                
                if has_subtitles:
                    cursor = conn.execute("SELECT COUNT(*) as subtitle_count FROM subtitles")
                    subtitle_stats = cursor.fetchone()
                    subtitle_count = subtitle_stats['subtitle_count'] if subtitle_stats else 0
                else:
                    subtitle_count = 0
                
                return {
                    "channel_id": channel_name,
                    "channel_name": channel_name,
                    "display_name": sample_video['channel_name'] if sample_video else channel_name,
                    "video_count": stats['video_count'] if stats else 0,
                    "subtitle_count": subtitle_count,
                    "first_video": stats['first_video'] if stats else None,
                    "latest_video": stats['latest_video'] if stats else None,
                    "has_subtitles": has_subtitles,
                    "database_path": db_path,
                    "sample_url": sample_video['url'] if sample_video else None
                }
                
        except Exception as e:
            logger.error(f"Failed to get metadata for channel {channel_name}: {str(e)}")
            return None
    
    def get_channel_videos(self, channel_name: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get videos for a specific channel."""
        try:
            db_path = os.path.join(self.downloads_dir, f"{channel_name}.db")
            
            if not os.path.exists(db_path):
                logger.warning(f"Database not found for channel {channel_name}")
                return []
            
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                cursor = conn.execute("""
                    SELECT video_id, title, summary, upload_date, url, duration,
                           view_count, like_count, comment_count, channel_name
                    FROM videos
                    ORDER BY upload_date DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))
                
                videos = []
                for row in cursor.fetchall():
                    videos.append({
                        "video_id": row['video_id'],
                        "title": row['title'],
                        "summary": row['summary'],
                        "upload_date": row['upload_date'],
                        "url": row['url'],
                        "duration": row['duration'],
                        "view_count": row['view_count'],
                        "like_count": row['like_count'],
                        "comment_count": row['comment_count'],
                        "channel_name": row['channel_name']
                    })
                
                return videos
                
        except Exception as e:
            logger.error(f"Failed to get videos for channel {channel_name}: {str(e)}")
            return []
    
    def search_channel_content(self, channel_name: str, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search content within a specific channel."""
        try:
            db_path = os.path.join(self.downloads_dir, f"{channel_name}.db")
            
            if not os.path.exists(db_path):
                return []
            
            results = []
            
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Search in video summaries and titles
                cursor = conn.execute("""
                    SELECT video_id, title, summary, upload_date, url, 'summary' as content_type
                    FROM videos
                    WHERE title LIKE ? OR summary LIKE ?
                    ORDER BY upload_date DESC
                    LIMIT ?
                """, (f'%{query}%', f'%{query}%', limit))
                
                for row in cursor.fetchall():
                    relevance_score = self._calculate_relevance_score(query, row['title'], row['summary'])
                    results.append({
                        "video_id": row['video_id'],
                        "title": row['title'],
                        "content": row['summary'],
                        "content_type": row['content_type'],
                        "upload_date": row['upload_date'],
                        "url": row['url'],
                        "relevance_score": relevance_score
                    })
                
                # Search in subtitles if available
                try:
                    cursor = conn.execute("""
                        SELECT v.video_id, v.title, s.content, s.start_time, v.upload_date, v.url, 'subtitle' as content_type
                        FROM videos v
                        JOIN subtitles s ON v.video_id = s.video_id
                        WHERE s.content LIKE ?
                        ORDER BY v.upload_date DESC, s.start_time ASC
                        LIMIT ?
                    """, (f'%{query}%', limit))
                    
                    for row in cursor.fetchall():
                        relevance_score = self._calculate_relevance_score(query, row['title'], row['content'])
                        results.append({
                            "video_id": row['video_id'],
                            "title": row['title'],
                            "content": row['content'],
                            "content_type": row['content_type'],
                            "timestamp": row['start_time'],
                            "upload_date": row['upload_date'],
                            "url": row['url'],
                            "relevance_score": relevance_score
                        })
                        
                except sqlite3.OperationalError:
                    # Subtitles table doesn't exist
                    pass
            
            # Sort by relevance score
            results.sort(key=lambda x: x['relevance_score'], reverse=True)
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Failed to search content in channel {channel_name}: {str(e)}")
            return []
    
    def _calculate_relevance_score(self, query: str, title: str, content: str) -> float:
        """Calculate relevance score for search results."""
        query_words = query.lower().split()
        title_lower = title.lower()
        content_lower = content.lower()
        
        score = 0.0
        total_words = len(query_words)
        
        for word in query_words:
            if word in title_lower:
                score += 0.4  # Title matches are more important
            if word in content_lower:
                score += 0.2
        
        return min(1.0, score / total_words) if total_words > 0 else 0.0
    
    def get_channel_analytics(self, channel_name: str, days: int = 30) -> Dict[str, Any]:
        """Get analytics data for a specific channel."""
        try:
            db_path = os.path.join(self.downloads_dir, f"{channel_name}.db")
            
            if not os.path.exists(db_path):
                return {}
            
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Get date range
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                
                # Basic stats
                cursor = conn.execute("""
                    SELECT COUNT(*) as total_videos,
                           AVG(view_count) as avg_views,
                           AVG(like_count) as avg_likes,
                           AVG(comment_count) as avg_comments,
                           SUM(view_count) as total_views
                    FROM videos
                    WHERE upload_date >= ?
                """, (start_date.strftime('%Y-%m-%d'),))
                
                stats = cursor.fetchone()
                
                # Video upload trends
                cursor = conn.execute("""
                    SELECT DATE(upload_date) as date, COUNT(*) as video_count
                    FROM videos
                    WHERE upload_date >= ?
                    GROUP BY DATE(upload_date)
                    ORDER BY date
                """, (start_date.strftime('%Y-%m-%d'),))
                
                upload_trends = [dict(row) for row in cursor.fetchall()]
                
                # Top performing videos
                cursor = conn.execute("""
                    SELECT video_id, title, view_count, like_count, upload_date, url
                    FROM videos
                    WHERE upload_date >= ?
                    ORDER BY view_count DESC
                    LIMIT 10
                """, (start_date.strftime('%Y-%m-%d'),))
                
                top_videos = [dict(row) for row in cursor.fetchall()]
                
                return {
                    "channel_name": channel_name,
                    "period_days": days,
                    "stats": {
                        "total_videos": stats['total_videos'] if stats else 0,
                        "avg_views": round(stats['avg_views'] or 0, 2),
                        "avg_likes": round(stats['avg_likes'] or 0, 2),
                        "avg_comments": round(stats['avg_comments'] or 0, 2),
                        "total_views": stats['total_views'] if stats else 0
                    },
                    "upload_trends": upload_trends,
                    "top_videos": top_videos
                }
                
        except Exception as e:
            logger.error(f"Failed to get analytics for channel {channel_name}: {str(e)}")
            return {}
    
    def get_video_details(self, channel_name: str, video_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information for a specific video."""
        try:
            db_path = os.path.join(self.downloads_dir, f"{channel_name}.db")
            
            if not os.path.exists(db_path):
                return None
            
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Get video details
                cursor = conn.execute("""
                    SELECT * FROM videos WHERE video_id = ?
                """, (video_id,))
                
                video = cursor.fetchone()
                if not video:
                    return None
                
                video_data = dict(video)
                
                # Get subtitles if available
                try:
                    cursor = conn.execute("""
                        SELECT start_time, end_time, content
                        FROM subtitles
                        WHERE video_id = ?
                        ORDER BY start_time
                    """, (video_id,))
                    
                    subtitles = [dict(row) for row in cursor.fetchall()]
                    video_data['subtitles'] = subtitles
                    
                except sqlite3.OperationalError:
                    video_data['subtitles'] = []
                
                return video_data
                
        except Exception as e:
            logger.error(f"Failed to get video details for {video_id} in channel {channel_name}: {str(e)}")
            return None
    
    def get_all_channels_summary(self) -> Dict[str, Any]:
        """Get summary statistics for all channels."""
        try:
            channels = self.get_available_channels()
            
            total_videos = sum(ch['video_count'] for ch in channels)
            total_subtitles = sum(ch['subtitle_count'] for ch in channels)
            
            # Get latest activity
            latest_videos = []
            for channel in channels:
                if channel['latest_video']:
                    latest_videos.append({
                        "channel": channel['channel_name'],
                        "date": channel['latest_video']
                    })
            
            latest_videos.sort(key=lambda x: x['date'], reverse=True)
            
            return {
                "total_channels": len(channels),
                "total_videos": total_videos,
                "total_subtitles": total_subtitles,
                "channels_with_subtitles": sum(1 for ch in channels if ch['has_subtitles']),
                "latest_activity": latest_videos[:5],
                "channels": channels
            }
            
        except Exception as e:
            logger.error(f"Failed to get channels summary: {str(e)}")
            return {
                "total_channels": 0,
                "total_videos": 0,
                "total_subtitles": 0,
                "channels_with_subtitles": 0,
                "latest_activity": [],
                "channels": []
            }