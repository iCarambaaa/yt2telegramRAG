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
    def __init__(self, cookies_file: str = None, retry_attempts: int = 3, retry_delay_seconds: int = 5, debug_mode: bool = False):
        self.cookies_file = cookies_file
        self.retry_attempts = retry_attempts
        self.retry_delay_seconds = retry_delay_seconds
        self.debug_mode = debug_mode or os.getenv('YTDLP_DEBUG', '').lower() in ('true', '1', 'yes')

    @api_retry
    def get_latest_videos(self, channel_id: str, max_results: int = 5) -> List[Video]:
        """Fetch latest videos from YouTube channel with enhanced bot detection bypass"""
        logger.info("Fetching latest videos", max_results=max_results, channel_id=channel_id)
        
        # Enhanced yt-dlp options to bypass YouTube restrictions
        ydl_opts = {
            "extract_flat": True,
            "skip_download": True,
            "quiet": not self.debug_mode,  # Enable verbose output in debug mode
            "verbose": self.debug_mode,  # Enable verbose logging in debug mode
            "playlist_items": f"1-{max_results}",
            # Add delay to avoid rate limiting (YouTube allows ~300 videos/hour for guests)
            "sleep_interval": 5,  # Increased from 2 to 5 seconds
            "max_sleep_interval": 10,  # Increased from 5 to 10 seconds
            "sleep_requests": 1,  # Add delay between requests during data extraction
            # Use multiple client fallbacks for better success rate
            "extractor_args": {
                "youtube": {
                    "player_client": ["mweb", "web", "tv", "ios"],  # Multiple clients for fallback
                    "player_skip": ["configs", "webpage"],  # Skip more requests to reduce detection
                    "pot_trace": self.debug_mode,  # Enable PO Token debugging in debug mode
                },
                "youtubetab": {
                    "skip": ["authcheck", "webpage"]  # Skip auth check and webpage for public content
                }
            },
            # Add user agent to appear more browser-like
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            },
            # Error handling improvements
            "no_abort_on_error": True,  # Continue on errors
            "ignoreerrors": True,  # Ignore download errors
        }
        
        # Add debug-specific options
        if self.debug_mode:
            ydl_opts.update({
                "write_pages": True,  # Write raw HTML pages for debugging
                "print_traffic": True,  # Display HTTP traffic
                "dump_single_json": True,  # Output single JSON line per video
            })
            logger.info("Debug mode enabled - verbose output and page dumping active")

        if self.cookies_file:
            # Handle relative paths from project root
            if not os.path.isabs(self.cookies_file):
                cookies_path = os.path.join(os.getcwd(), self.cookies_file)
            else:
                cookies_path = self.cookies_file
            
            # Only add cookies if file exists and is readable
            if os.path.exists(cookies_path) and os.path.getsize(cookies_path) > 0:
                ydl_opts["cookiefile"] = cookies_path
                logger.debug("Using cookies file", path=cookies_path)
            else:
                logger.warning("Cookies file not found or empty, proceeding without cookies", path=cookies_path)

        channel_url = f"https://www.youtube.com/channel/{channel_id}/videos"
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
            entries = info.get("entries", [])
            
            videos = []
            for entry in entries:
                if entry and entry.get('id'):
                    video = Video.from_yt_dlp(entry, channel_id)
                    videos.append(video)
        
        logger.info("Successfully fetched videos", count=len(videos))
        return videos

    def download_subtitles(self, video_id: str, subtitle_preferences: List[str], output_dir: str) -> str:
        """Download subtitles for a video with smart priority logic"""
        logger.info("Downloading subtitles for video", video_id=video_id)
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # First, get video info to determine original language with enhanced options
        info_opts = {
            "skip_download": True,
            "quiet": True,
            # Add delay to avoid rate limiting
            "sleep_interval": 1,
            "max_sleep_interval": 3,
            "extractor_args": {
                "youtube": {
                    "player_client": ["mweb", "web", "tv"],  # Multiple clients for better success
                    "player_skip": ["configs"],  # Reduce requests
                }
            },
            # Browser-like headers
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        }
        
        if self.cookies_file:
            # Handle relative paths from project root
            if not os.path.isabs(self.cookies_file):
                cookies_path = os.path.join(os.getcwd(), self.cookies_file)
            else:
                cookies_path = self.cookies_file
            
            # Only add cookies if file exists and is readable
            if os.path.exists(cookies_path) and os.path.getsize(cookies_path) > 0:
                info_opts["cookiefile"] = cookies_path

        video_url = f"https://www.youtube.com/watch?v={video_id}"
        original_language = "en"  # Default fallback
        
        # Try to detect original language
        try:
            with yt_dlp.YoutubeDL(info_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                original_language = info.get('language') or info.get('original_language') or "en"
                logger.info("Detected original language", language=original_language)
        except Exception as e:
            logger.warning("Could not detect original language, using 'en'", error=str(e))
        
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
        
        logger.info("Subtitle priority order", priority_languages=priority_languages)
        
        # Try each language in priority order until we find one
        for attempt in range(self.retry_attempts):
            try:
                for lang in priority_languages:
                    logger.info("Trying to download subtitles", language=lang)
                    
                    # Download only this specific language with enhanced options
                    ydl_opts = {
                        "writesubtitles": True,
                        "writeautomaticsub": True,
                        "subtitleslangs": [lang],  # Only try one language at a time
                        "subtitlesformat": "vtt",
                        "skip_download": True,
                        "outtmpl": str(output_path / f"{video_id}.%(ext)s"),
                        "quiet": True,
                        # Add delays to avoid rate limiting
                        "sleep_interval": 1,
                        "max_sleep_interval": 3,
                        "sleep_subtitles": 1,
                        "extractor_args": {
                            "youtube": {
                                "player_client": ["mweb", "web", "tv"],  # Multiple clients
                                "player_skip": ["configs"],  # Reduce requests
                            }
                        },
                        # Browser-like headers
                        "http_headers": {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                        }
                    }

                    if self.cookies_file and os.path.exists(cookies_path) and os.path.getsize(cookies_path) > 0:
                        ydl_opts["cookiefile"] = cookies_path

                    try:
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            ydl.download([video_url])
                        
                        # Check if subtitle was downloaded
                        subtitle_file = output_path / f"{video_id}.{lang}.vtt"
                        if subtitle_file.exists():
                            logger.info("Successfully downloaded subtitles", file_path=str(subtitle_file), language=lang)
                            return str(subtitle_file)
                        else:
                            logger.debug("No subtitles available for language", language=lang)
                            
                    except Exception as lang_error:
                        logger.debug("Failed to download subtitles", language=lang, error=str(lang_error))
                        continue  # Try next language
                
                # If we get here, no languages worked
                logger.warning("No subtitles found in any priority language", video_id=video_id)
                return None
                
            except Exception as e:
                logger.warning("Subtitle download attempt failed", attempt=attempt + 1, error=str(e))
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay_seconds)
                else:
                    logger.error("Failed to download subtitles after all attempts", retry_attempts=self.retry_attempts)
                    return None

    def analyze_error(self, error: Exception) -> dict:
        """Analyze yt-dlp errors and provide debugging suggestions"""
        error_str = str(error).lower()
        error_analysis = {
            "error_type": "unknown",
            "suggestions": [],
            "debug_commands": []
        }
        
        # Rate limiting / YouTube restrictions
        if any(phrase in error_str for phrase in [
            "content isn't available", "try again later", "429", "too many requests"
        ]):
            error_analysis.update({
                "error_type": "rate_limiting",
                "suggestions": [
                    "Increase sleep intervals between requests",
                    "Use cookies from a logged-in browser session",
                    "Try using different client types (mweb, tv, ios)",
                    "Reduce concurrent requests"
                ],
                "debug_commands": [
                    "yt-dlp -v --sleep-interval 10 --max-sleep-interval 20 <url>",
                    "yt-dlp --cookies-from-browser chrome <url>",
                    "yt-dlp --extractor-args 'youtube:player_client=mweb' <url>"
                ]
            })
        
        # Authentication / Access issues
        elif any(phrase in error_str for phrase in [
            "private video", "members-only", "sign in", "login required"
        ]):
            error_analysis.update({
                "error_type": "authentication",
                "suggestions": [
                    "Export cookies from a logged-in browser session",
                    "Use --cookies-from-browser or --cookies options",
                    "Ensure you have access to the content"
                ],
                "debug_commands": [
                    "yt-dlp --cookies-from-browser chrome <url>",
                    "yt-dlp --cookies cookies.txt <url>"
                ]
            })
        
        # Network / Connection issues
        elif any(phrase in error_str for phrase in [
            "network", "connection", "timeout", "ssl", "certificate"
        ]):
            error_analysis.update({
                "error_type": "network",
                "suggestions": [
                    "Check internet connection",
                    "Try --no-check-certificates for SSL issues",
                    "Use --source-address to specify network interface",
                    "Add --user-agent with browser user agent"
                ],
                "debug_commands": [
                    "yt-dlp --no-check-certificates <url>",
                    "yt-dlp --print-traffic <url>",
                    "yt-dlp --user-agent 'Mozilla/5.0...' <url>"
                ]
            })
        
        # Format / Extraction issues
        elif any(phrase in error_str for phrase in [
            "no video formats", "unable to extract", "format not available"
        ]):
            error_analysis.update({
                "error_type": "extraction",
                "suggestions": [
                    "Check available formats with -F flag",
                    "Try different format selection",
                    "Use --check-formats to verify format availability",
                    "Try different client types"
                ],
                "debug_commands": [
                    "yt-dlp -F <url>",
                    "yt-dlp --check-all-formats <url>",
                    "yt-dlp --write-pages <url>",
                    "yt-dlp --extractor-args 'youtube:player_client=tv' <url>"
                ]
            })
        
        return error_analysis

    def debug_video_access(self, video_id: str) -> dict:
        """Debug video access issues with comprehensive testing"""
        logger.info("Starting comprehensive video access debugging", video_id=video_id)
        
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        debug_results = {
            "video_id": video_id,
            "tests": {},
            "recommendations": []
        }
        
        # Test 1: Basic info extraction
        try:
            basic_opts = {"quiet": True, "skip_download": True}
            with yt_dlp.YoutubeDL(basic_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                debug_results["tests"]["basic_extraction"] = {
                    "success": True,
                    "title": info.get("title"),
                    "availability": info.get("availability"),
                    "live_status": info.get("live_status")
                }
        except Exception as e:
            debug_results["tests"]["basic_extraction"] = {
                "success": False,
                "error": str(e),
                "analysis": self.analyze_error(e)
            }
        
        # Test 2: Format availability
        try:
            format_opts = {"quiet": True, "listformats": True}
            with yt_dlp.YoutubeDL(format_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                formats = info.get("formats", [])
                debug_results["tests"]["format_check"] = {
                    "success": True,
                    "format_count": len(formats),
                    "has_video": any(f.get("vcodec") != "none" for f in formats),
                    "has_audio": any(f.get("acodec") != "none" for f in formats)
                }
        except Exception as e:
            debug_results["tests"]["format_check"] = {
                "success": False,
                "error": str(e)
            }
        
        # Test 3: Subtitle availability
        try:
            sub_opts = {
                "quiet": True,
                "skip_download": True,
                "writesubtitles": True,
                "writeautomaticsub": True,
                "listsubtitles": True
            }
            with yt_dlp.YoutubeDL(sub_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                subtitles = info.get("subtitles", {})
                auto_subs = info.get("automatic_captions", {})
                debug_results["tests"]["subtitle_check"] = {
                    "success": True,
                    "manual_subtitles": list(subtitles.keys()),
                    "auto_subtitles": list(auto_subs.keys())
                }
        except Exception as e:
            debug_results["tests"]["subtitle_check"] = {
                "success": False,
                "error": str(e)
            }
        
        # Generate recommendations based on test results
        if not debug_results["tests"]["basic_extraction"]["success"]:
            debug_results["recommendations"].extend([
                "Video may be private, deleted, or region-blocked",
                "Try using cookies from a logged-in browser session",
                "Check if video ID is correct"
            ])
        
        if debug_results["tests"].get("format_check", {}).get("success") and \
           debug_results["tests"]["format_check"].get("format_count", 0) == 0:
            debug_results["recommendations"].extend([
                "No formats available - video may be live-only or restricted",
                "Try different client types (mweb, tv, ios)"
            ])
        
        return debug_results