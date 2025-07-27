#!/usr/bin/env python3
"""
Advanced YouTube subtitle downloader with multiple format support
"""

import os
import re
import json
import sqlite3
import logging
import argparse
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
import yt_dlp
from datetime import datetime
import xml.etree.ElementTree as ET

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AdvancedSubtitleDownloader:
    """Advanced subtitle downloader with multiple format support"""
    
    def __init__(self, db_path: str = None, output_dir: str = None):
        self.db_path = db_path or os.path.expanduser("~/youtube_monitor.db")
        self.output_dir = Path(output_dir or "subtitles")
        self.output_dir.mkdir(exist_ok=True)
        self.temp_dir = Path("temp_subtitles")
        self.temp_dir.mkdir(exist_ok=True)
        
    def setup_database(self):
        """Initialize database connection"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_videos (
                video_id TEXT PRIMARY KEY,
                title TEXT,
                channel_name TEXT,
                published_at TEXT,
                duration INTEGER,
                view_count INTEGER,
                like_count INTEGER,
                summary TEXT,
                subtitles TEXT,
                subtitle_formats TEXT,
                subtitle_languages TEXT,
                processed_at TEXT,
                subtitle_status TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subtitle_formats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT,
                format_name TEXT,
                language TEXT,
                file_path TEXT,
                file_size INTEGER,
                download_time TEXT,
                FOREIGN KEY (video_id) REFERENCES processed_videos (video_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def extract_video_info(self, video_url: str) -> Optional[Dict]:
        """Extract comprehensive video information"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                
                return {
                    'video_id': info.get('id'),
                    'title': info.get('title'),
                    'channel': info.get('uploader'),
                    'channel_id': info.get('channel_id'),
                    'duration': info.get('duration'),
                    'view_count': info.get('view_count'),
                    'like_count': info.get('like_count'),
                    'upload_date': info.get('upload_date'),
                    'description': info.get('description'),
                    'tags': info.get('tags', []),
                    'categories': info.get('categories', []),
                    'subtitles': info.get('subtitles', {}),
                    'automatic_captions': info.get('automatic_captions', {}),
                }
                
        except Exception as e:
            logger.error(f"Error extracting video info: {e}")
            return None
    
    def download_subtitles(self, video_url: str, languages: List[str] = None, 
                          formats: List[str] = None) -> Dict[str, Any]:
        """
        Download subtitles in multiple formats and languages
        
        Args:
            video_url: YouTube video URL
            languages: List of language codes (default: ['en'])
            formats: List of subtitle formats (default: ['vtt', 'srt', 'json'])
            
        Returns:
            Dictionary with download results
        """
        languages = languages or ['en']
        formats = formats or ['vtt', 'srt', 'json3']
        
        results = {
            'video_info': None,
            'downloads': {},
            'errors': [],
            'metadata': {}
        }
        
        # Get video info first
        video_info = self.extract_video_info(video_url)
        if not video_info:
            results['errors'].append("Could not extract video information")
            return results
        
        results['video_info'] = video_info
        video_id = video_info['video_id']
        
        # Check available subtitles
        available_subtitles = {}
        available_subtitles.update(video_info['subtitles'])
        available_subtitles.update(video_info['automatic_captions'])
        
        if not available_subtitles:
            results['errors'].append("No subtitles available for this video")
            return results
        
        # Create output directory for this video
        video_dir = self.output_dir / f"{video_id}_{video_info['title'][:50]}"
        video_dir.mkdir(exist_ok=True)
        
        # Download subtitles for each language and format
        for lang in languages:
            if lang not in available_subtitles:
                results['errors'].append(f"Language '{lang}' not available")
                continue
            
            lang_dir = video_dir / lang
            lang_dir.mkdir(exist_ok=True)
            
            subtitle_data = available_subtitles[lang]
            results['downloads'][lang] = {}
            
            for fmt in formats:
                try:
                    # Find the format in subtitle data
                    format_info = None
                    for sub_fmt in subtitle_data:
                        if sub_fmt['ext'] == fmt:
                            format_info = sub_fmt
                            break
                    
                    if not format_info:
                        results['errors'].append(f"Format '{fmt}' not available for language '{lang}'")
                        continue
                    
                    # Download subtitle
                    output_file = lang_dir / f"subtitles.{fmt}"
                    
                    ydl_opts = {
                        'writesubtitles': True,
                        'writeautomaticsub': True,
                        'subtitleslangs': [lang],
                        'subtitlesformat': fmt,
                        'skip_download': True,
                        'outtmpl': str(output_file.with_suffix('')),
                        'quiet': True,
                        'no_warnings': True,
                    }
                    
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([video_url])
                    
                    # Check if file was created
                    actual_file = output_file
                    if fmt == 'json3':
                        actual_file = output_file.with_suffix('.json3')
                    
                    if actual_file.exists():
                        file_size = actual_file.stat().st_size
                        
                        # Save to database
                        self._save_subtitle_format(
                            video_id, fmt, lang, str(actual_file), file_size
                        )
                        
                        results['downloads'][lang][fmt] = {
                            'file_path': str(actual_file),
                            'file_size': file_size,
                            'format_info': format_info
                        }
                        
                        # Parse and store content if it's text-based
                        if fmt in ['vtt', 'srt']:
                            content = self._parse_subtitle_file(actual_file, fmt)
                            results['metadata'][f"{lang}_{fmt}"] = content
                        
                    else:
                        results['errors'].append(f"Failed to create file: {actual_file}")
                        
                except Exception as e:
                    error_msg = f"Error downloading {lang}.{fmt}: {str(e)}"
                    results['errors'].append(error_msg)
                    logger.error(error_msg)
        
        return results
    
    def _parse_subtitle_file(self, file_path: Path, format_type: str) -> Dict:
        """Parse subtitle file and extract metadata"""
        try:
            content = file_path.read_text(encoding='utf-8')
            
            if format_type == 'vtt':
                return self._parse_vtt(content)
            elif format_type == 'srt':
                return self._parse_srt(content)
            
        except Exception as e:
            logger.error(f"Error parsing subtitle file: {e}")
            return {}
    
    def _parse_vtt(self, content: str) -> Dict:
        """Parse VTT subtitle format"""
        lines = content.split('\n')
        
        # Skip header
        start_index = 0
        for i, line in enumerate(lines):
            if line.strip() == "WEBVTT":
                start_index = i + 1
                break
        
        entries = []
        current_entry = {}
        
        for line in lines[start_index:]:
            line = line.strip()
            
            if not line:
                if current_entry:
                    entries.append(current_entry)
                    current_entry = {}
                continue
            
            if '-->' in line:
                # Timing line
                parts = line.split('-->')
                if len(parts) == 2:
                    current_entry['start'] = parts[0].strip()
                    current_entry['end'] = parts[1].strip()
            elif line and not line.startswith('NOTE') and not line.startswith('STYLE'):
                # Text content
                if 'text' not in current_entry:
                    current_entry['text'] = []
                current_entry['text'].append(line)
        
        if current_entry:
            entries.append(current_entry)
        
        # Clean up text
        for entry in entries:
            if 'text' in entry:
                entry['text'] = ' '.join(entry['text']).strip()
        
        return {
            'format': 'vtt',
            'entries': entries,
            'total_entries': len(entries),
            'total_duration': self._calculate_duration(entries)
        }
    
    def _parse_srt(self, content: str) -> Dict:
        """Parse SRT subtitle format"""
        lines = content.strip().split('\n')
        
        entries = []
        current_entry = {}
        
        for line in lines:
            line = line.strip()
            
            if line.isdigit():
                # Subtitle number
                if current_entry:
                    entries.append(current_entry)
                current_entry = {'number': int(line)}
            elif '-->' in line:
                # Timing line
                parts = line.split('-->')
                if len(parts) == 2:
                    current_entry['start'] = parts[0].strip()
                    current_entry['end'] = parts[1].strip()
            elif line and current_entry:
                # Text content
                if 'text' not in current_entry:
                    current_entry['text'] = []
                current_entry['text'].append(line)
        
        if current_entry:
            entries.append(current_entry)
        
        # Clean up text
        for entry in entries:
            if 'text' in entry:
                entry['text'] = ' '.join(entry['text']).strip()
        
        return {
            'format': 'srt',
            'entries': entries,
            'total_entries': len(entries),
            'total_duration': self._calculate_duration(entries)
        }
    
    def _calculate_duration(self, entries: List[Dict]) -> float:
        """Calculate total duration from subtitle entries"""
        if not entries or len(entries) < 2:
            return 0.0
        
        try:
            # Parse first and last timestamps
            first_start = self._parse_time(entries[0].get('start', '00:00:00.000'))
            last_end = self._parse_time(entries[-1].get('end', '00:00:00.000'))
            
            return last_end - first_start
        except:
            return 0.0
    
    def _parse_time(self, time_str: str) -> float:
        """Parse time string to seconds"""
        try:
            # Handle both VTT and SRT time formats
            time_str = time_str.replace(',', '.')
            
            if ' --> ' in time_str:
                time_str = time_str.split(' --> ')[0]
            
            parts = time_str.split(':')
            if len(parts) == 3:
                hours = float(parts[0])
                minutes = float(parts[1])
                seconds = float(parts[2])
                return hours * 3600 + minutes * 60 + seconds
        except:
            pass
        
        return 0.0
    
    def _save_subtitle_format(self, video_id: str, format_name: str, 
                            language: str, file_path: str, file_size: int):
        """Save subtitle format information to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO subtitle_formats 
                (video_id, format_name, language, file_path, file_size, download_time)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                video_id, format_name, language, file_path, file_size,
                datetime.now().isoformat() + 'Z'
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving subtitle format: {e}")
    
    def get_subtitle_summary(self, video_id: str) -> Dict:
        """Get summary of available subtitles for a video"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get video info
            cursor.execute('''
                SELECT * FROM processed_videos WHERE video_id = ?
            ''', (video_id,))
            
            video_data = cursor.fetchone()
            
            # Get subtitle formats
            cursor.execute('''
                SELECT format_name, language, file_path, file_size, download_time
                FROM subtitle_formats
                WHERE video_id = ?
                ORDER BY language, format_name
            ''', (video_id,))
            
            formats = cursor.fetchall()
            
            conn.close()
            
            return {
                'video': video_data,
                'formats': formats,
                'total_formats': len(formats)
            }
            
        except Exception as e:
            logger.error(f"Error getting subtitle summary: {e}")
            return {}
    
    def process_video(self, video_url: str, languages: List[str] = None, 
                     formats: List[str] = None) -> bool:
        """Process a video and download all subtitles"""
        logger.info(f"Processing video: {video_url}")
        
        results = self.download_subtitles(video_url, languages, formats)
        
        if results['video_info']:
            self._save_video_info(results['video_info'], results)
            return True
        
        return False
    
    def _save_video_info(self, video_info: Dict, download_results: Dict):
        """Save video information to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Format published date
            published_date = video_info['upload_date']
            if published_date:
                try:
                    date_obj = datetime.strptime(published_date, '%Y%m%d')
                    published_iso = date_obj.isoformat() + 'Z'
                except:
                    published_iso = datetime.now().isoformat() + 'Z'
            else:
                published_iso = datetime.now().isoformat() + 'Z'
            
            # Collect subtitle formats and languages
            formats = []
            languages = []
            for lang, fmt_dict in download_results['downloads'].items():
                languages.append(lang)
                formats.extend(fmt_dict.keys())
            
            cursor.execute('''
                INSERT OR REPLACE INTO processed_videos 
                (video_id, title, channel_name, published_at, duration, view_count, 
                 like_count, summary, subtitle_formats, subtitle_languages, 
                 processed_at, subtitle_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                video_info['video_id'],
                video_info['title'],
                video_info['channel'],
                published_iso,
                video_info['duration'],
                video_info['view_count'],
                video_info['like_count'],
                video_info['description'][:500],  # Truncate description
                ','.join(set(formats)),
                ','.join(set(languages)),
                datetime.now().isoformat() + 'Z',
                'downloaded'
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving video info: {e}")

def main():
    """Main function for testing"""
    parser = argparse.ArgumentParser(description="Advanced YouTube subtitle downloader")
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument("--languages", "-l", default="en", 
                       help="Comma-separated language codes (default: en)")
    parser.add_argument("--formats", "-f", default="vtt,srt,json3", 
                       help="Comma-separated formats (default: vtt,srt,json3)")
    parser.add_argument("--output-dir", "-o", help="Output directory")
    parser.add_argument("--db-path", help="Database path")
    
    args = parser.parse_args()
    
    downloader = AdvancedSubtitleDownloader(args.db_path, args.output_dir)
    downloader.setup_database()
    
    languages = args.languages.split(',')
    formats = args.formats.split(',')
    
    success = downloader.process_video(args.url, languages, formats)
    
    if success:
        print("✅ Video processed successfully!")
        
        # Show summary
        video_info = downloader.extract_video_info(args.url)
        if video_info:
            summary = downloader.get_subtitle_summary(video_info['video_id'])
            print(f"\n📊 Subtitle Summary:")
            print(f"Video: {video_info['title']}")
            print(f"Total formats: {summary.get('total_formats', 0)}")
            
            for fmt in summary.get('formats', []):
                print(f"  - {fmt[1]} ({fmt[0]}): {fmt[2]} ({fmt[3]} bytes)")
    else:
        print("❌ Failed to process video")

if __name__ == "__main__":
    main()