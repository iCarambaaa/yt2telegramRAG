import yt_dlp
import os
import time
from typing import List
from pathlib import Path

from ..models.video import Video
from ..utils.retry import api_retry
from ..utils.logging_config import LoggerFactory

logger = LoggerFactory.create_logger(__name__)

class YouTubeService:
    def __init__(self, cookies_file: str = None, retry_attempts: int = 3, retry_delay_seconds: int = 5):
        self.cookies_file = cookies_file
        self.retry_attempts = retry_attempts
        self.retry_delay_seconds = retry_delay_seconds

    @api_retry
    def get_latest_videos(self, channel_id: str, max_results: int = 5) -> List[Video]:
        """Fetch latest videos from YouTube channel"""
        logger.info("Fetching latest videos", max_results=max_results, channel_id=channel_id)
        
        # Try with full metadata first, fallback to flat extraction
        ydl_opts = {
            "extract_flat": False,  # Get full metadata including upload_date
            "skip_download": True,
            "quiet": True,
            "playlist_items": f"1-{max_results}",
            "extractor_args": {
                "youtube": {
                    "player_client": ["web", "android"],  # Try multiple clients
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
        
        videos = []
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(channel_url, download=False)
                entries = info.get("entries", [])
                
                for entry in entries:
                    if entry and entry.get('id'):
                        video = Video.from_yt_dlp(entry, channel_id)
                        videos.append(video)
        except Exception as e:
            logger.warning("Full metadata extraction failed, trying flat extraction", error=str(e))
            # Fallback to flat extraction
            ydl_opts["extract_flat"] = True
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(channel_url, download=False)
                    entries = info.get("entries", [])
                    
                    for entry in entries:
                        if entry and entry.get('id'):
                            video = Video.from_yt_dlp(entry, channel_id)
                            videos.append(video)
            except Exception as e2:
                logger.error("Both full and flat extraction failed", error=str(e2))
                raise e2
        
        logger.info("Successfully fetched videos", count=len(videos))
        return videos

    def download_subtitles(self, video_id: str, subtitle_preferences: List[str], output_dir: str) -> str:
        """Download subtitles for a video with smart priority logic"""
        logger.info("Downloading subtitles for video", video_id=video_id)
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # First, get video info to determine original language
        info_opts = {
            "skip_download": True,
            "quiet": True,
            "extractor_args": {
                "youtube": {
                    "player_client": ["web"],
                    "player_skip": ["configs", "webpage"]
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
        available_subtitles = {}
        try:
            with yt_dlp.YoutubeDL(info_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                original_language = info.get('language') or info.get('original_language') or "en"
                
                # Get available subtitles info
                subtitles = info.get('subtitles', {})
                automatic_captions = info.get('automatic_captions', {})
                
                # Log available subtitle languages
                manual_langs = list(subtitles.keys())
                auto_langs = list(automatic_captions.keys())
                
                logger.info("Detected video language and available subtitles", 
                           original_language=original_language,
                           manual_subtitles=manual_langs,
                           auto_captions=auto_langs)
                
                available_subtitles = {
                    'manual': subtitles,
                    'auto': automatic_captions
                }
                
        except Exception as e:
            logger.warning("Could not detect original language or subtitles, using defaults", error=str(e))
        
        # Build smart priority list based on your requirements:
        # 1. Original language manual subtitles (highest priority)
        # 2. Original language auto-generated 
        # 3. Manual CC in preferences
        # 4. Auto-generated CC in preferences
        priority_languages = []
        
        # 1. Original language manual subtitles (highest priority)
        if original_language in available_subtitles.get('manual', {}):
            priority_languages.append(original_language)
            logger.info("Found manual subtitles in original language", language=original_language)
        
        # 2. Original language auto-generated
        if original_language in available_subtitles.get('auto', {}):
            priority_languages.append(original_language)
            logger.info("Found auto-generated subtitles in original language", language=original_language)
        
        # 3. Manual CC in user preferences
        for pref in (subtitle_preferences or ["en"]):
            if pref in available_subtitles.get('manual', {}) and pref not in [original_language]:
                priority_languages.append(pref)
                logger.info("Found manual subtitles in preference language", language=pref)
        
        # 4. Auto-generated CC in user preferences  
        for pref in (subtitle_preferences or ["en"]):
            if pref in available_subtitles.get('auto', {}) and pref not in priority_languages:
                priority_languages.append(pref)
                logger.info("Found auto-generated subtitles in preference language", language=pref)
        
        # Fallback: try any available languages
        for lang in available_subtitles.get('manual', {}):
            if lang not in priority_languages:
                priority_languages.append(lang)
        
        for lang in available_subtitles.get('auto', {}):
            if lang not in priority_languages:
                priority_languages.append(lang)
        
        logger.info("Subtitle priority order", priority_languages=priority_languages, original_language=original_language)
        
        # If no priority languages available, log the issue clearly
        if not priority_languages:
            logger.error("No subtitle languages available for video", video_id=video_id, 
                        available_manual=list(available_subtitles.get('manual', {}).keys()),
                        available_auto=list(available_subtitles.get('auto', {}).keys()))
            return None
        
        # Try each language in priority order until we find one
        for attempt in range(self.retry_attempts):
            try:
                for lang in priority_languages:
                    logger.info("Trying to download subtitles", language=lang, attempt=attempt + 1)
                    
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
                                "player_client": ["web"],
                                "player_skip": ["configs", "webpage"]
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
                            file_size = subtitle_file.stat().st_size
                            logger.info("Successfully downloaded subtitles", 
                                       file_path=str(subtitle_file), 
                                       language=lang, 
                                       file_size_bytes=file_size,
                                       is_original_language=(lang == original_language or lang == f"a.{original_language}"))
                            return str(subtitle_file)
                        else:
                            logger.debug("No subtitles available for language", language=lang)
                            
                    except Exception as lang_error:
                        error_msg = str(lang_error)
                        if "not available on this app" in error_msg or "Sign in to confirm your age" in error_msg:
                            logger.warning("Video is age-restricted or region-blocked", 
                                         video_id=video_id, language=lang, error=error_msg)
                        else:
                            logger.debug("Failed to download subtitles", language=lang, error=error_msg)
                        continue  # Try next language
                
                # If we get here, no languages worked
                logger.warning("No subtitles found in any priority language", 
                             video_id=video_id, 
                             tried_languages=priority_languages,
                             original_language=original_language)
                return None
                
            except Exception as e:
                error_msg = str(e)
                if "not available on this app" in error_msg or "Sign in to confirm your age" in error_msg:
                    logger.error("Video is age-restricted or region-blocked, cannot download subtitles", 
                               video_id=video_id, error=error_msg)
                    return None  # Don't retry for access issues
                
                logger.warning("Subtitle download attempt failed", attempt=attempt + 1, error=error_msg)
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay_seconds)
                else:
                    logger.error("Failed to download subtitles after all attempts", 
                               retry_attempts=self.retry_attempts, video_id=video_id)
                    return None