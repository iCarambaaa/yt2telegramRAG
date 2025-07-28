
import yt_dlp
import logging
from typing import List, Dict
import asyncio

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class YouTubeClient:
    def __init__(self, cookies_file: str = None, retry_attempts: int = 3, retry_delay_seconds: int = 5):
        self.cookies_file = cookies_file
        self.retry_attempts = retry_attempts
        self.retry_delay_seconds = retry_delay_seconds

    async def get_latest_videos(self, channel_id: str, max_results: int = 5) -> List[Dict]:
        logger.info(f"Fetching latest {max_results} videos for channel: {channel_id}")
        ydl_opts = {
            "extract_flat": True,
            "skip_download": True,
            "quiet": True,
            "playlist_items": f"1-{max_results}", # Fetch only the latest N videos
        }

        if self.cookies_file:
            ydl_opts["cookiefile"] = self.cookies_file

        channel_url = f"https://www.youtube.com/channel/{channel_id}/videos"
        videos = []

        for attempt in range(self.retry_attempts):
            try:
                # Run yt-dlp in a thread to avoid blocking
                def _fetch_videos():
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(channel_url, download=False)
                        entries = info.get("entries", [])
                        for entry in entries:
                            try:
                                if entry and entry.get('id'): # Ensure it's a valid video entry
                                    videos.append({
                                        "id": entry["id"],
                                        "title": entry.get("title", ""),
                                        "published_at": entry.get("upload_date", ""), # YYYYMMDD format
                                        "channel_id": channel_id,
                                    })
                            except Exception as e:
                                logger.error(f"Error processing video entry from yt-dlp: {entry}. Error: {e}")
                        return videos
                
                videos = await asyncio.to_thread(_fetch_videos)
                logger.info(f"Found {len(videos)} latest videos for channel {channel_id}")
                return videos
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}/{self.retry_attempts} failed to fetch videos for channel {channel_id}: {e}")
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay_seconds)
        logger.error(f"Failed to fetch videos for channel {channel_id} after {self.retry_attempts} attempts.")
        return []
