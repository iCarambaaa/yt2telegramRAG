#!/usr/bin/env python3
"""
Extract and clean subtitles from YouTube videos using yt-dlp
"""

import os
import re
import json
import sqlite3
import logging
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import yt_dlp
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SubtitleExtractor:
    """Extract and clean subtitles from YouTube videos"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.expanduser("~/youtube_monitor.db")
        self.temp_dir = Path("temp_subtitles")
        self.temp_dir.mkdir(exist_ok=True)
        
    def setup_database(self):
        """Initialize database connection"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_videos (
                video_id TEXT PRIMARY KEY,
                title TEXT,
                channel_name TEXT,
                published_at TEXT,
                summary TEXT,
                subtitles TEXT,
                processed_at TEXT,
                subtitle_language TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def extract_subtitles(self, video_url: str, language: str = 'en') -> Optional[Dict]:
        """
        Extract subtitles from a YouTube video
        
        Args:
            video_url: YouTube video URL
            language: Language code for subtitles (default: 'en')
            
        Returns:
            Dictionary with subtitle data or None if extraction fails
        """
        try:
            # Extract video ID from URL
            video_id = self._extract_video_id(video_url)
            if not video_id:
                logger.error(f"Could not extract video ID from URL: {video_url}")
                return None
            
            # Setup yt-dlp options
            ydl_opts = {
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': [language],
                'skip_download': True,
                'outtmpl': str(self.temp_dir / f'%(id)s.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
            }
            
            # Extract video info and subtitles
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Get video info
                info = ydl.extract_info(video_url, download=False)
                
                # Check if subtitles are available
                subtitles = info.get('subtitles', {})
                automatic_captions = info.get('automatic_captions', {})
                
                # Try to get manual subtitles first, then automatic
                subtitle_data = None
                if language in subtitles and subtitles[language]:
                    subtitle_data = subtitles[language]
                    subtitle_type = 'manual'
                elif language in automatic_captions and automatic_captions[language]:
                    subtitle_data = automatic_captions[language]
                    subtitle_type = 'automatic'
                else:
                    logger.warning(f"No subtitles found for language: {language}")
                    return None
                
                # Download subtitle file
                subtitle_file = None
                for fmt in subtitle_data:
                    if fmt['ext'] == 'vtt':
                        subtitle_file = ydl.prepare_filename(info).replace('.%(ext)s', f'.{language}.vtt')
                        ydl.download([video_url])
                        break
                
                if not subtitle_file or not os.path.exists(subtitle_file):
                    logger.error("Could not download subtitle file")
                    return None
                
                # Read and clean subtitles
                with open(subtitle_file, 'r', encoding='utf-8') as f:
                    raw_subtitles = f.read()
                
                cleaned_subtitles = self._clean_vtt_subtitles(raw_subtitles)
                
                # Clean up temporary file
                os.remove(subtitle_file)
                
                return {
                    'video_id': video_id,
                    'title': info.get('title', ''),
                    'channel': info.get('uploader', ''),
                    'published_date': info.get('upload_date', ''),
                    'subtitles': cleaned_subtitles,
                    'subtitle_type': subtitle_type,
                    'language': language
                }
                
        except Exception as e:
            logger.error(f"Error extracting subtitles: {e}")
            return None
    
    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL"""
        patterns = [
            r'(?:v=|\\/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed\\/)([0-9A-Za-z_-]{11})',
            r'(?:youtu\\.be\\/)([0-9A-Za-z_-]{11})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def _clean_vtt_subtitles(self, vtt_content: str) -> str:
        """
        Clean VTT subtitle content
        
        Args:
            vtt_content: Raw VTT subtitle content
            
        Returns:
            Cleaned subtitle text
        """
        # Remove VTT header
        lines = vtt_content.split('\n')
        
        # Skip header lines
        start_index = 0
        for i, line in enumerate(lines):
            if line.strip() == "WEBVTT":
                start_index = i + 1
                break
        
        # Process remaining lines
        cleaned_lines = []
        current_text = []
        
        for line in lines[start_index:]:
            line = line.strip()
            
            # Skip empty lines and timing information
            if not line or '-->' in line or line.isdigit():
                if current_text:
                    # Join current text and add to cleaned lines
                    text = ' '.join(current_text).strip()
                    if text:
                        cleaned_lines.append(text)
                    current_text = []
                continue
            
            # Add text content
            if line and not line.startswith('NOTE') and not line.startswith('STYLE'):
                # Remove HTML tags
                line = re.sub(r'<[^>]+>', '', line)
                # Remove extra spaces
                line = re.sub(r'\s+', ' ', line).strip()
                if line:
                    current_text.append(line)
        
        # Add any remaining text
        if current_text:
            text = ' '.join(current_text).strip()
            if text:
                cleaned_lines.append(text)
        
        # Join all text with proper spacing
        result = ' '.join(cleaned_lines)
        
        # Clean up common issues
        result = re.sub(r'\s+', ' ', result)  # Multiple spaces
        result = re.sub(r'(\w)([.!?])(\w)', r'\1\2 \3', result)  # Missing spaces after punctuation
        result = result.strip()
        
        return result
    
    def save_to_database(self, subtitle_data: Dict, summary: str = None):
        """Save subtitle data to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Format published date
            published_date = subtitle_data['published_date']
            if published_date:
                # Convert YYYYMMDD to ISO format
                try:
                    date_obj = datetime.strptime(published_date, '%Y%m%d')
                    published_iso = date_obj.isoformat() + 'Z'
                except:
                    published_iso = datetime.now().isoformat() + 'Z'
            else:
                published_iso = datetime.now().isoformat() + 'Z'
            
            cursor.execute('''
                INSERT OR REPLACE INTO processed_videos 
                (video_id, title, channel_name, published_at, summary, subtitles, processed_at, subtitle_language)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                subtitle_data['video_id'],
                subtitle_data['title'],
                subtitle_data['channel'],
                published_iso,
                summary or '',
                subtitle_data['subtitles'],
                datetime.now().isoformat() + 'Z',
                subtitle_data['language']
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Saved subtitles for video: {subtitle_data['title']}")
            
        except Exception as e:
            logger.error(f"Error saving to database: {e}")
    
    def process_video(self, video_url: str, language: str = 'en', summary: str = None) -> bool:
        """
        Process a single video: extract subtitles and save to database
        
        Args:
            video_url: YouTube video URL
            language: Language code for subtitles
            summary: Optional summary text
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Processing video: {video_url}")
        
        subtitle_data = self.extract_subtitles(video_url, language)
        if subtitle_data:
            self.save_to_database(subtitle_data, summary)
            logger.info(f"Successfully processed: {subtitle_data['title']}")
            return True
        else:
            logger.error(f"Failed to process video: {video_url}")
            return False
    
    def get_video_stats(self) -> Dict:
        """Get statistics about processed videos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_videos,
                    COUNT(DISTINCT channel_name) as unique_channels,
                    MIN(published_at) as oldest_video,
                    MAX(published_at) as newest_video,
                    subtitle_language
                FROM processed_videos
                GROUP BY subtitle_language
            ''')
            
            stats = {
                'total_videos': 0,
                'unique_channels': 0,
                'languages': {},
                'oldest_video': None,
                'newest_video': None
            }
            
            for row in cursor.fetchall():
                stats['total_videos'] += row[0]
                stats['unique_channels'] = max(stats['unique_channels'], row[1])
                
                lang = row[4] or 'unknown'
                stats['languages'][lang] = row[0]
                
                if row[2] and (not stats['oldest_video'] or row[2] < stats['oldest_video']):
                    stats['oldest_video'] = row[2]
                if row[3] and (not stats['newest_video'] or row[3] > stats['newest_video']):
                    stats['newest_video'] = row[3]
            
            conn.close()
            return stats
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}

def main():
    """Main function for testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract and clean subtitles from YouTube videos")
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument("--language", "-l", default="en", help="Subtitle language code (default: en)")
    parser.add_argument("--summary", "-s", help="Summary text to save with subtitles")
    parser.add_argument("--db-path", help="Database path")
    
    args = parser.parse_args()
    
    extractor = SubtitleExtractor(args.db_path)
    extractor.setup_database()
    
    success = extractor.process_video(args.url, args.language, args.summary)
    if success:
        print("✅ Video processed successfully!")
        
        # Show stats
        stats = extractor.get_video_stats()
        print(f"\n📊 Database Stats:")
        print(f"Total videos: {stats.get('total_videos', 0)}")
        print(f"Unique channels: {stats.get('unique_channels', 0)}")
        print(f"Languages: {stats.get('languages', {})}")
    else:
        print("❌ Failed to process video")

if __name__ == "__main__":
    main()