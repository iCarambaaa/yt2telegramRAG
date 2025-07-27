

import yaml
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
import asyncio
from typing import Dict, Any, Optional

from channel_manager.glob import find_channel_configs
from channel_manager.database import DatabaseManager
from channel_manager.youtube_dlp import SubtitleDownloader
from channel_manager.subtitle_cleaner import SubtitleCleaner
from channel_manager.telegram_bot import TelegramNotifier
from channel_manager.youtube_client import YouTubeClient
from channel_manager.llm_summarizer import LLMSummarizer
from channel_manager.exceptions import ConfigurationError, DatabaseError, YouTubeAPIError, SubtitleProcessingError, LLMError, TelegramAPIError, ValidationError
from channel_manager.logging_config import setup_logging_from_env # Import the new logging setup
from channel_manager.validators import InputValidator # Import the new validator

# Setup logging early
setup_logging_from_env()
logger = logging.getLogger(__name__) # Use the configured logger

def load_config(config_path: str) -> Dict[str, Any]:
    """Load and validate configuration from YAML file."""
    try:
        # Use the validator to load and validate the YAML file
        config = InputValidator.validate_yaml_file(config_path)
        return config
    except ValidationError as e:
        raise ConfigurationError(f"Invalid configuration in {config_path}: {e}")
    except Exception as e:
        raise ConfigurationError(f"Failed to load config from {config_path}: {e}")

def is_due_for_processing(last_check_str: Optional[str], schedule_type: str) -> bool:
    """Check if channel is due for processing based on schedule."""
    if not last_check_str:
        return True  # Never processed before

    try:
        last_check = datetime.fromisoformat(last_check_str)
    except ValueError:
        logger.warning(f"Invalid last_check format: {last_check_str}, treating as never processed")
        return True
    
    now = datetime.now()

    if schedule_type == "daily":
        return (now - last_check) >= timedelta(days=1)
    elif schedule_type == "weekly":
        return (now - last_check) >= timedelta(weeks=1)
    elif schedule_type == "monthly":
        return (now - last_check) >= timedelta(days=30)  # Approximation for monthly
    else:
        logger.warning(f"Unknown schedule type: {schedule_type}")
        return False

async def process_channel(config: Dict[str, Any]) -> None:
    """Process a single channel configuration."""
    try:
        # Validate the channel config structure
        config = InputValidator.validate_channel_config(config)
    except ValidationError as e:
        logger.error(f"Invalid channel configuration: {e}")
        return

    channel_name = config.get('name')
    channel_id = config.get('channel_id')
    db_path = config.get('db_path')
    schedule_type = config.get('schedule')
    
    # These fields are validated by InputValidator.validate_channel_config
    # but we still need to retrieve them.
    cookies_file = config.get('cookies_file')
    subtitle_preferences = config.get('subtitles', [])
    telegram_bots_config = config.get('telegram_bots', [])
    llm_config = config.get('llm_config', {})
    max_videos_to_fetch = config.get('max_videos_to_fetch', 5)
    retry_attempts = config.get('retry_attempts', 3)
    retry_delay_seconds = config.get('retry_delay_seconds', 5)

    logger.info(f"Processing channel: {channel_name} (ID: {channel_id})")

    try:
        db_manager = DatabaseManager(db_path)
    except DatabaseError as e:
        logger.error(f"Failed to initialize database for {channel_name}: {e}")
        return

    async with db_manager: # Use async context manager
        last_check = await db_manager.get_last_check(channel_id)

        if not is_due_for_processing(last_check, schedule_type):
            logger.info(f"Channel {channel_name} not due for processing yet.")
            return

        youtube_client = YouTubeClient(
            cookies_file=cookies_file,
            retry_attempts=retry_attempts,
            retry_delay_seconds=retry_delay_seconds
        )
        subtitle_downloader = SubtitleDownloader(
            cookies_file=cookies_file,
            retry_attempts=retry_attempts,
            retry_delay_seconds=retry_delay_seconds
        )
        subtitle_cleaner = SubtitleCleaner()
        telegram_notifier = TelegramNotifier(
            telegram_bots_config,
            retry_attempts=retry_attempts,
            retry_delay_seconds=retry_delay_seconds
        )
        llm_summarizer = LLMSummarizer(
            llm_config,
            retry_attempts=retry_attempts,
            retry_delay_seconds=retry_delay_seconds
        )

        try:
            latest_videos = await youtube_client.get_latest_videos(
                channel_id,
                max_videos_to_fetch
            )
        except YouTubeAPIError as e:
            logger.error(f"Failed to fetch latest videos for {channel_name}: {e}")
            return

        for video in latest_videos:
            # Handle different date formats gracefully
            published_at = video.get('published_at')
            if published_at:
                try:
                    # Try to parse ISO format first
                    if isinstance(published_at, str):
                        if len(published_at) == 8 and published_at.isdigit():
                            # YYYYMMDD format
                            published_at_iso = datetime.strptime(published_at, '%Y%m%d').isoformat()
                        else:
                            # Try ISO format
                            published_at_iso = datetime.fromisoformat(published_at.replace('Z', '+00:00')).isoformat()
                    else:
                        # Already a datetime or other format
                        published_at_iso = str(published_at)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid published_at format: {published_at}, using current time")
                    published_at_iso = datetime.now().isoformat()
            else:
                published_at_iso = datetime.now().isoformat()
            
            video['published_at'] = published_at_iso

            try:
                if await db_manager.is_video_processed(video['id']):
                    logger.info(f"Video {video['id']} already processed. Skipping.")
                    continue

                logger.info(f"Processing video: {video.get('title', 'Unknown')}")

                # Create a temporary directory for raw subtitles
                temp_subtitle_dir = Path("channel_manager") / "downloads" / str(channel_id) / "raw_subtitles"
                temp_subtitle_dir.mkdir(parents=True, exist_ok=True)

                raw_subtitle_path = await subtitle_downloader.download_subtitles(
                    video['id'], subtitle_preferences, str(temp_subtitle_dir)
                )

                cleaned_subtitles = ""
                if raw_subtitle_path and Path(raw_subtitle_path).exists():
                    cleaned_subtitles = subtitle_cleaner.process_subtitle_file(raw_subtitle_path)
                    # Clean up raw subtitle file after processing
                    try:
                        os.remove(raw_subtitle_path)
                    except OSError as e:
                        logger.warning(f"Failed to remove raw subtitle file: {e}")
                else:
                    logger.warning(f"No raw subtitles downloaded for video {video['id']}. Cannot clean.")

                # Generate summary using LLM
                generated_summary = await llm_summarizer.summarize(cleaned_subtitles)

                video['raw_subtitle_path'] = raw_subtitle_path if raw_subtitle_path else ""
                video['cleaned_subtitles'] = cleaned_subtitles
                video['summary'] = generated_summary

                await db_manager.add_video(video)
                logger.info(f"Video {video['id']} added to database.")

                # Send Telegram notification
                title = video.get('title', 'Unknown Title')
                message = (
                    f"New video from {channel_name}: {title}\n\n"
                    f"Summary: {generated_summary}\n"
                    f"Link: https://www.youtube.com/watch?v={video['id']}"
                )
                await telegram_notifier.send_message(message)

            except Exception as e:
                logger.error(f"Error processing video {video.get('id', 'Unknown')}: {e}")
                continue

        await db_manager.update_last_check(channel_id, datetime.now().isoformat())
        logger.info(f"Finished processing channel: {channel_name}")

async def main():
    config_files = find_channel_configs()
    if not config_files:
        logger.warning("No channel configuration files found. Exiting.")
        return

    for config_file in config_files:
        try:
            config = load_config(config_file)
            await process_channel(config)
        except Exception as e:
            logger.error(f"Error processing config file {config_file}: {e}")

if __name__ == "__main__":
    # Load environment variables from .env file at the project root
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(main())
