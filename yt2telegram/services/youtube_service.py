import yt_dlp
import logging
import os
from typing import List
from pathlib import Path

from ..models.video import Video
from ..utils.retry import api_retry

logger = logging.getLogger(__name__)

class YouTubeService:
    def __init__(self, cookies_file: str = None):
        self.cookies_file = cookies_file

    @api_retry
    def get_latest_videos(self, channel_id: str, max_results: int = 5) -> List[Video]:
        """Fetch latest videos from YouTube channel"""
        logger.info(f"Fetching latest {max_results} videos for channel: {channel_id}")
        
        ydl_opts = {
            "extract_flat": True,
            "skip_download": True,
            "quiet": True,
            "playlist_items": f"1-{max_results}",
            "extractor_args": {
                "youtube": {
                    "player_client": ["web"],  # Only use web client when cookies are needed
                    "player_skip": ["webpage"]
                }
            }
        }

        if self.cookies_file:
            # Handle relative paths from project root
            if not os.path.isabs(self.cookies_file):
                cookies_path = os.path.join(os.getcwd(), self.cookies_file)
            else:
                cookies_path = self.cookies_file
            ydl_opts["cookiefile"] = cookies_path

        channel_url = f"https://www.youtube.com/channel/{channel_id}/videos"
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
            entries = info.get("entries", [])
            
            videos = []
            for entry in entries:
                if entry and entry.get('id'):
                    video = Video.from_yt_dlp(entry, channel_id)
                    videos.append(video)
        
        logger.info(f"Successfully fetched {len(videos)} videos")
        return videos

    def download_subtitles(self, video_id: str, subtitle_preferences: List[str], output_dir: str) -> str:
        """Download subtitles for a video with smart priority logic"""
        logger.info(f"Downloading subtitles for video: {video_id}")
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # First, get video info to determine original language
        info_opts = {
            "skip_download": True,
            "quiet": True,
            "extractor_args": {
                "youtube": {
                    "player_client": ["web"],  # Only use web client when cookies are needed
                    "player_skip": ["webpage"]
                }
            }
        }
        
        if self.cookies_file:
            # Handle relative paths from project root
            if not os.path.isabs(self.cookies_file):
                cookies_path = os.path.join(os.getcwd(), self.cookies_file)
            else:
                cookies_path = self.cookies_file
            info_opts["cookiefile"] = cookies_path

        video_url = f"https://www.youtube.com/watch?v={video_id}"
        original_language = "en"  # Default fallback
        
        # Try to detect original language
        try:
            with yt_dlp.YoutubeDL(info_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                original_language = info.get('language') or info.get('original_language') or "en"
                logger.info(f"Detected original language: {original_language}")
        except Exception as e:
            logger.warning(f"Could not detect original language, using 'en': {e}")
        
        # Build smart priority list: original language manual -> original language auto -> preferences
        priority_languages = []
        
        # 1. Original language manual subtitles (highest priority)
        priority_languages.append(original_language)
        
        # 2. Original language auto-generated (if different format)
        if original_language != "en":
            priority_languages.extend([f"a.{original_language}", f"{original_language}-orig"])
        priority_languages.extend([f"a.en", "en-orig"])
        
        # 3. User preferences as fallback
        for pref in (subtitle_preferences or ["en"]):
            if pref not in priority_languages:
                priority_languages.append(pref)
        
        logger.info(f"Subtitle priority order: {priority_languages}")
        
        # Try each language in priority order until we find one
        for attempt in range(self.retry_attempts):
            try:
                for lang in priority_languages:
                    logger.info(f"Trying to download subtitles in language: {lang}")
                    
                    # Download only this specific language
                    ydl_opts = {
                        "writesubtitles": True,
                        "writeautomaticsub": True,
                        "subtitleslangs": [lang],  # Only try one language at a time
                        "subtitlesformat": "vtt",
                        "skip_download": True,
                        "outtmpl": str(output_path / f"{video_id}.%(ext)s"),
                        "quiet": True,
                        "extractor_args": {
                            "youtube": {
                                "player_client": ["web"],  # Only use web client when cookies are needed
                                "player_skip": ["webpage"]
                            }
                        }
                    }

                    if self.cookies_file:
                        ydl_opts["cookiefile"] = cookies_path

                    try:
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            ydl.download([video_url])
                        
                        # Check if subtitle was downloaded
                        subtitle_file = output_path / f"{video_id}.{lang}.vtt"
                        if subtitle_file.exists():
                            logger.info(f"Successfully downloaded subtitles: {subtitle_file} (language: {lang})")
                            return str(subtitle_file)
                        else:
                            logger.debug(f"No subtitles available for language: {lang}")
                            
                    except Exception as lang_error:
                        logger.debug(f"Failed to download {lang} subtitles: {lang_error}")
                        continue  # Try next language
                
                # If we get here, no languages worked
                logger.warning(f"No subtitles found for video {video_id} in any priority language")
                return None
                
            except Exception as e:
                logger.warning(f"Subtitle download attempt {attempt + 1} failed: {e}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay_seconds)
                else:
                    logger.error(f"Failed to download subtitles after {self.retry_attempts} attempts")
                    return None