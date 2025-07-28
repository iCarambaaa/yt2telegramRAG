import yt_dlp
import logging
from pathlib import Path
import asyncio
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class SubtitleDownloader:
    def __init__(self, cookies_file=None, retry_attempts: int = 3, retry_delay_seconds: int = 5):
        self.cookies_file = cookies_file
        self.retry_attempts = retry_attempts
        self.retry_delay_seconds = retry_delay_seconds

    async def download_subtitles(self, video_id, subtitle_preferences, download_path):
        """Download subtitles asynchronously for a given video ID."""
        Path(download_path).mkdir(parents=True, exist_ok=True)
        
        for attempt in range(self.retry_attempts):
            for preference in subtitle_preferences:
                lang = preference['lang']
                sub_type = preference['type']
                
                # Construct the expected output path for yt-dlp
                expected_subtitle_path = Path(download_path) / f"{video_id}.{lang}.vtt"
                
                ydl_opts = {
                    'writesubtitles': sub_type == 'manual',
                    'writeautomaticsub': sub_type == 'automatic',
                    'subtitleslangs': [lang],
                    'skip_download': True,
                    'outtmpl': str(Path(download_path) / video_id), # yt-dlp adds .lang.vtt
                    'quiet': True,
                    'no_warnings': True, # Suppress some yt-dlp warnings in logs
                    'socket_timeout': 30, # Add timeout to prevent hanging
                }
                
                if self.cookies_file:
                    ydl_opts['cookiefile'] = self.cookies_file
                
                try:
                    def download():
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            result = ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
                        return result
                    
                    result = await asyncio.to_thread(download)
                    
                    # Check if subtitle file was created
                    if expected_subtitle_path.exists():
                        logger.info(f"Successfully downloaded {sub_type} subtitles in {lang} for video {video_id}")
                        return str(expected_subtitle_path)
                    else:
                        logger.warning(f"Subtitle file not found for video {video_id} after download attempt")
                        
                except Exception as e:
                    logger.warning(f"Attempt {attempt + 1} failed for {sub_type} subtitles in {lang} for video {video_id}: {e}")
                    if attempt < self.retry_attempts - 1:
                        logger.info(f"Retrying in {self.retry_delay_seconds} seconds...")
                        await asyncio.sleep(self.retry_delay_seconds)
                    else:
                        logger.error(f"All retry attempts failed for {sub_type} subtitles in {lang} for video {video_id}")
        
        logger.error(f"Failed to download any subtitles for video {video_id} after all attempts")
        return None
