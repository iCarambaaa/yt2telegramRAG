#!/usr/bin/env python3
"""
Single Video Processor - Multimodal Pipeline

Process a single YouTube video through the multimodal AI pipeline and send
the summary to Telegram. This is a standalone utility for on-demand video
processing without channel configuration.

Usage:
    python process_single_video.py <VIDEO_URL_OR_ID>

Examples:
    python process_single_video.py https://www.youtube.com/watch?v=dQw4w9WgXcQ
    python process_single_video.py dQw4w9WgXcQ

Environment Variables Required:
    - TELEGRAM_BOT_TOKEN: Bot authentication token
    - TELEGRAM_CHAT_ID: Target chat/channel ID
    - LLM_PROVIDER_API_KEY: Primary AI service API key
    - MODEL: Primary LLM model name (e.g., gpt-4o-mini)
    - BASE_URL: Primary LLM API endpoint

Optional Environment Variables:
    - COOKIES_FILE: Path to YouTube cookies for age-restricted content
    - ENABLE_MULTI_MODEL: Set to 'false' to disable multi-model (enabled by default)
    - PRIMARY_MODEL: Override primary model (default: openai/gpt-4o)
    - SECONDARY_MODEL: Override secondary model (default: anthropic/claude-3.5-sonnet)
    - SYNTHESIS_MODEL: Override synthesis model (default: deepseek/deepseek-chat-v3-0324)
"""

import os
import sys
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from yt2telegram.utils.logging_config import setup_logging, LoggerFactory
from yt2telegram.models.video import Video
from yt2telegram.services.youtube_service import YouTubeService
from yt2telegram.services.telegram_service import TelegramService
from yt2telegram.services.llm_service import LLMService
from yt2telegram.services.multi_model_llm_service import MultiModelLLMService
from yt2telegram.utils.subtitle_cleaner import SubtitleCleaner


# Setup logging
setup_logging()
logger = LoggerFactory.create_logger(__name__)


def extract_video_id(input_str: str) -> str:
    """Extract YouTube video ID from URL or validate direct ID.
    
    SECURITY: Validates video ID format to prevent injection attacks
    
    Args:
        input_str: YouTube URL or video ID
        
    Returns:
        str: Validated 11-character video ID
        
    Raises:
        ValueError: If video ID cannot be extracted or is invalid
    """
    # If it's already a valid video ID (11 chars, alphanumeric + _ -)
    if re.match(r'^[a-zA-Z0-9_-]{11}$', input_str):
        return input_str
    
    # Try to extract from various YouTube URL formats
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        r'youtube\.com/v/([a-zA-Z0-9_-]{11})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, input_str)
        if match:
            return match.group(1)
    
    raise ValueError(f"Could not extract valid video ID from: {input_str}")


def get_video_metadata(youtube_service: YouTubeService, video_id: str) -> Video:
    """Fetch video metadata from YouTube.
    
    CRITICAL: Video metadata is required for processing
    FALLBACK: Returns minimal Video object if metadata fetch fails
    
    Args:
        youtube_service: Initialized YouTube service
        video_id: YouTube video ID
        
    Returns:
        Video: Video object with metadata
    """
    logger.info("Fetching video metadata", video_id=video_id)
    
    try:
        # Use yt-dlp to get video info
        import yt_dlp
        
        # DECISION: Client strategy based on cookie availability
        # With cookies: use only web client (android doesn't support cookies)
        # Without cookies: use web + android fallback for better success rate
        player_clients = ["web"]
        if not youtube_service.cookies_file:
            player_clients.append("android")
        
        ydl_opts = {
            "skip_download": True,
            "quiet": True,
            "extractor_args": {
                "youtube": {
                    "player_client": player_clients,
                    "player_skip": ["webpage"]
                }
            }
        }
        
        if youtube_service.cookies_file:
            cookies_path = youtube_service.cookies_file
            if not os.path.isabs(cookies_path):
                cookies_path = os.path.join(os.getcwd(), cookies_path)
            ydl_opts["cookiefile"] = cookies_path
        
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            # Extract channel ID and language
            channel_id = info.get('channel_id', 'unknown')
            language = info.get('language') or info.get('original_language') or 'en'
            
            # Create Video object from metadata
            video = Video.from_yt_dlp(info, channel_id)
            
            # Store language as an attribute (not in Video model, but useful for processing)
            video.language = language
            
            logger.info("Successfully fetched video metadata",
                       video_id=video_id,
                       title=video.title,
                       channel_id=channel_id,
                       published_at=video.published_at,
                       language=language)
            
            return video
            
    except Exception as e:
        logger.warning("Could not fetch full metadata, using minimal info", error=str(e))
        # FALLBACK: Create minimal Video object
        video = Video(
            id=video_id,
            title=f"Video {video_id}",
            channel_id="unknown",
            published_at=datetime.now().strftime("%Y-%m-%d")
        )
        video.language = 'en'  # Default to English if metadata fetch fails
        return video


def build_llm_config() -> dict:
    """Build LLM configuration from environment variables.
    
    DECISION: Multi-model by default for best quality, can be disabled with ENABLE_MULTI_MODEL=false
    SECURITY: API keys loaded from environment, never hardcoded
    
    Returns:
        dict: Complete LLM configuration
    """
    enable_multi_model = os.getenv('ENABLE_MULTI_MODEL', 'true').lower() == 'true'
    
    config = {
        'llm_api_key_env': 'LLM_PROVIDER_API_KEY',
        'llm_base_url_env': 'BASE_URL',
        'llm_model': os.getenv('MODEL', 'gpt-4o-mini'),
        'llm_prompt_template': """Summarize the following YouTube video content. Focus on main topics, key points, and important takeaways.

Content: {content}"""
    }
    
    if enable_multi_model:
        config['multi_model'] = {
            'enabled': True,
            'primary_model': os.getenv('PRIMARY_MODEL', 'openai/gpt-4o'),
            'secondary_model': os.getenv('SECONDARY_MODEL', 'anthropic/claude-3.5-sonnet'),
            'synthesis_model': os.getenv('SYNTHESIS_MODEL', 'deepseek/deepseek-chat-v3-0324'),
            'cost_threshold_tokens': int(os.getenv('COST_THRESHOLD_TOKENS', '50000')),
            'fallback_strategy': os.getenv('FALLBACK_STRATEGY', 'best_summary'),
        }
        
        logger.info("Multi-model processing enabled",
                   primary_model=config['multi_model']['primary_model'],
                   secondary_model=config['multi_model']['secondary_model'],
                   synthesis_model=config['multi_model']['synthesis_model'])
    else:
        logger.info("Single-model processing enabled", model=config['llm_model'])
    
    return config


def process_video(video_url_or_id: str, save_to_db: bool = False) -> bool:
    """Process a single video through the complete pipeline.
    
    CRITICAL: Main processing pipeline - failures affect user experience
    FALLBACK: Graceful degradation at each stage
    
    Processing Pipeline:
    1. Extract and validate video ID
    2. Initialize all services
    3. Fetch video metadata
    4. Download and clean subtitles
    5. Generate AI summary (single or multi-model)
    6. Send formatted message to Telegram
    
    Args:
        video_url_or_id: YouTube URL or video ID
        
    Returns:
        bool: True if processing completed successfully
    """
    try:
        # Extract video ID
        video_id = extract_video_id(video_url_or_id)
        logger.info("Processing video", video_id=video_id, input=video_url_or_id)
        
        # Initialize services
        logger.info("Initializing services")
        
        cookies_file = os.getenv('COOKIES_FILE')
        youtube_service = YouTubeService(
            cookies_file=cookies_file,
            retry_attempts=3,
            retry_delay_seconds=5
        )
        
        telegram_bots_config = [{
            'name': 'Main Bot',
            'token_env': 'TELEGRAM_BOT_TOKEN',
            'chat_id_env': 'TELEGRAM_CHAT_ID'
        }]
        telegram_service = TelegramService(bot_configs=telegram_bots_config)
        
        llm_config = build_llm_config()
        
        # Initialize appropriate LLM service
        multi_model_config = llm_config.get('multi_model', {})
        if multi_model_config.get('enabled', False):
            llm_service = MultiModelLLMService(llm_config=llm_config, channel_name="single_video")
        else:
            llm_service = LLMService(llm_config=llm_config)
        
        subtitle_cleaner = SubtitleCleaner()
        
        # Get video metadata
        video = get_video_metadata(youtube_service, video_id)
        
        # Download and clean subtitles
        logger.info("Downloading subtitles", video_id=video_id)
        temp_subtitle_dir = Path(f"yt2telegram/downloads/temp/raw_subtitles")
        
        # DECISION: Smart subtitle language selection
        # For German/Russian videos: prioritize original language
        # For other videos: use configured preferences or default to English
        subtitle_preferences = os.getenv('SUBTITLE_LANGUAGES', '').split(',') if os.getenv('SUBTITLE_LANGUAGES') else []
        
        # Detect video language from metadata
        video_language = getattr(video, 'language', None) or 'en'
        
        # Smart language priority: original language first for de/ru, then fallback
        if video_language in ['de', 'ru'] and video_language not in subtitle_preferences:
            subtitle_preferences = [video_language] + subtitle_preferences
            logger.info("Prioritizing original language for German/Russian video", 
                       original_language=video_language,
                       subtitle_preferences=subtitle_preferences)
        elif not subtitle_preferences:
            subtitle_preferences = ['en']
        
        raw_subtitle_path = youtube_service.download_subtitles(
            video_id,
            subtitle_preferences,
            str(temp_subtitle_dir)
        )
        
        if not raw_subtitle_path or not Path(raw_subtitle_path).exists():
            logger.error("No subtitles available for video", video_id=video_id)
            return False
        
        # Process subtitles
        with open(raw_subtitle_path, 'r', encoding='utf-8') as f:
            raw_subtitles = f.read()
        
        cleaned_subtitles = subtitle_cleaner.process_subtitle_file(raw_subtitle_path)
        
        # Clean up raw subtitle file
        try:
            os.remove(raw_subtitle_path)
        except Exception as e:
            logger.warning("Could not remove raw subtitle file", error=str(e))
        
        logger.info("Successfully processed subtitles",
                   video_id=video_id,
                   raw_size=len(raw_subtitles),
                   cleaned_size=len(cleaned_subtitles),
                   compression_ratio=f"{(1 - len(cleaned_subtitles)/len(raw_subtitles))*100:.1f}%")
        
        # Generate summary
        logger.info("Generating summary", video_id=video_id)
        
        summary = ""
        if hasattr(llm_service, 'summarize_enhanced'):
            # Multi-model service
            summary_result = llm_service.summarize_enhanced(cleaned_subtitles)
            summary = summary_result.get('final_summary', '')
            
            logger.info("Multi-model summary generated",
                       video_id=video_id,
                       summarization_method=summary_result.get('summarization_method'),
                       processing_time=summary_result.get('processing_time_seconds'),
                       cost_estimate=summary_result.get('cost_estimate'),
                       fallback_used=summary_result.get('fallback_used'))
        else:
            # Single-model service
            summary = llm_service.summarize(cleaned_subtitles)
            logger.info("Single-model summary generated", video_id=video_id)
        
        if not summary:
            logger.error("Failed to generate summary", video_id=video_id)
            return False
        
        logger.info("Successfully generated summary",
                   video_id=video_id,
                   summary_length=len(summary))
        
        # Send Telegram notification
        logger.info("Sending Telegram notification", video_id=video_id)
        
        success = telegram_service.send_video_notification(
            channel_name="Single Video",
            video_title=video.title,
            video_id=video_id,
            summary=summary,
            published_date=video.published_at
        )
        
        if success:
            logger.info("Successfully processed and sent video", video_id=video_id)
            return True
        else:
            logger.error("Failed to send Telegram notification", video_id=video_id)
            return False
            
    except Exception as e:
        logger.error("Error processing video", error=str(e), video_url_or_id=video_url_or_id)
        return False


def main():
    """Main entry point"""
    # Load environment variables
    load_dotenv()
    
    # Check for required arguments
    if len(sys.argv) < 2 or sys.argv[1] in ['-h', '--help', 'help']:
        print("Usage: python process_single_video.py <VIDEO_URL_OR_ID>")
        print("\nExamples:")
        print("  python process_single_video.py https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        print("  python process_single_video.py dQw4w9WgXcQ")
        print("\nEnvironment Variables:")
        print("  Required: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, LLM_PROVIDER_API_KEY")
        print("  Optional: ENABLE_MULTI_MODEL, COOKIES_FILE, SUBTITLE_LANGUAGES")
        print("\nFor full documentation, see: SINGLE_VIDEO_PROCESSING.md")
        sys.exit(0 if len(sys.argv) > 1 else 1)
    
    video_url_or_id = sys.argv[1]
    
    # Validate required environment variables
    required_vars = ['TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID', 'LLM_PROVIDER_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error("Missing required environment variables", missing=missing_vars)
        print(f"\nError: Missing required environment variables: {', '.join(missing_vars)}")
        print("\nPlease set these in your .env file or environment.")
        sys.exit(1)
    
    # Process the video
    logger.info("Starting single video processing", input=video_url_or_id)
    success = process_video(video_url_or_id)
    
    if success:
        logger.info("Video processing completed successfully")
        print("\n[SUCCESS] Video processed and sent to Telegram successfully!")
        sys.exit(0)
    else:
        logger.error("Video processing failed")
        print("\n[ERROR] Video processing failed. Check logs for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
