import yt_dlp
import logging
import asyncio
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SubtitleDownloader:
    def __init__(self, cookies_file=None, retry_attempts: int = 3, retry_delay_seconds: int = 5):
        self.cookies_file = cookies_file
        self.retry_attempts = retry_attempts
        self.retry_delay_seconds = retry_delay_seconds

    async def download_subtitles(self, video_id, subtitle_preferences, download_path):
        """Download subtitles asynchronously for a given video ID."""
        os.makedirs(download_path, exist_ok=True)
        
        for attempt in range(self.retry_attempts):
            for preference in subtitle_preferences:
                lang = preference['lang']
                sub_type = preference['type']
                try:
                    ydl_opts = {
                        'writesubtitles': sub_type == 'manual',
                        'writeautomaticsub': sub_type == 'automatic',
                        'subtitleslangs': [lang],
                        'skip_download': True,
                        'outtmpl': f'{download_path}/{video_id}',
                        'quiet': True,
                    }
                    if self.cookies_file:
                        ydl_opts['cookiefile'] = self.cookies_file

                    def _download():
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            ydl.download([f'https://www.youtube.com/watch?v={video_id}'])
                            subtitle_path = f'{download_path}/{video_id}.{lang}.vtt'
                            if os.path.exists(subtitle_path):
                                return subtitle_path
                        return None

                    result = await asyncio.to_thread(_download)
                    if result:
                        return result
                        
                except Exception as e:
                    logger.warning(f"Attempt {attempt + 1}/{self.retry_attempts} failed to download {sub_type} subtitles in {lang} for {video_id}: {e}")
            if attempt < self.retry_attempts - 1:
                await asyncio.sleep(self.retry_delay_seconds)
        logger.error(f"Failed to download subtitles for {video_id} after {self.retry_attempts} attempts.")
        return None