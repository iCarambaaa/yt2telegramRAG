import yaml
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
import asyncio
import re

# Simple logging setup to avoid the JSON logger issue
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

from channel_manager.glob import find_channel_configs
from channel_manager.database import DatabaseManager
from channel_manager.youtube_dlp import SubtitleDownloader
from channel_manager.subtitle_cleaner import SubtitleCleaner
from channel_manager.telegram_bot import TelegramNotifier
from channel_manager.youtube_client import YouTubeClient
from channel_manager.llm_summarizer import LLMSummarizer

def load_config(config_path):
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def is_due_for_processing(last_check_str, schedule_type):
    if not last_check_str:
        return True # Never processed before

    try:
        last_check = datetime.fromisoformat(last_check_str)
    except (ValueError, TypeError):
        return True # If we can't parse the date, process anyway
        
    now = datetime.now()

    if schedule_type == "daily":
        return (now - last_check) >= timedelta(days=1)
    elif schedule_type == "weekly":
        return (now - last_check) >= timedelta(weeks=1)
    elif schedule_type == "monthly":
        return (now - last_check) >= timedelta(days=30) # Approximation for monthly
    else:
        return False # Unknown schedule type

import re

def escape_markdown(text):
    """Escape special characters for Telegram MarkdownV2"""
    if not text:
        return text
    # Escape characters that need escaping in MarkdownV2
    # Order matters: escape backslash first, then other special characters
    escape_chars_pattern = r'([\\_*[\]()~`>#+-=|{}.!])'
    return re.sub(escape_chars_pattern, r'\\\\1', text)


async def process_channel(config):
    try:
        channel_name = config['name']
        channel_id = config['channel_id']
        db_path = config['db_path']
        schedule_type = config['schedule']
        cookies_file = config.get('cookies_file')
        subtitle_preferences = config.get('subtitles', [])
        telegram_bots_config = config.get('telegram_bots', [])
        llm_config = config.get('llm_config', {}) # Get llm_config
        max_videos_to_fetch = config.get('max_videos_to_fetch', 5) # Get max_videos_to_fetch
        retry_attempts = config.get('retry_attempts', 3)
        retry_delay_seconds = config.get('retry_delay_seconds', 5)

        logger.info(f"Processing channel: {channel_name} (ID: {channel_id})")

        # Ensure the database directory exists
        db_path_obj = Path(db_path)
        db_path_obj.parent.mkdir(parents=True, exist_ok=True)

        # Use the database manager correctly as an async context manager
        db_manager = DatabaseManager(db_path)
        
        async with db_manager:
            last_check = await db_manager.get_last_check(channel_id)

            if not is_due_for_processing(last_check, schedule_type):
                logger.info(f"Channel {channel_name} not due for processing yet.")
                return True

            youtube_client = YouTubeClient(cookies_file=cookies_file, retry_attempts=retry_attempts, retry_delay_seconds=retry_delay_seconds)
            subtitle_downloader = SubtitleDownloader(cookies_file=cookies_file, retry_attempts=retry_attempts, retry_delay_seconds=retry_delay_seconds)
            subtitle_cleaner = SubtitleCleaner()
            telegram_notifier = TelegramNotifier(telegram_bots_config, retry_attempts=retry_attempts, retry_delay_seconds=retry_delay_seconds)
            llm_summarizer = LLMSummarizer(llm_config, retry_attempts=retry_attempts, retry_delay_seconds=retry_delay_seconds)

            # Fix: await the get_latest_videos method
            latest_videos = await youtube_client.get_latest_videos(channel_id, max_videos_to_fetch)

            processed_count = 0
            for video in latest_videos:
                logger.debug(f"Video object before processing: {video}")
                logger.debug(f"Type of video object: {type(video)}")
                # Temporarily removed try...except to get full traceback
                logger.info(f"Processing video: {video.get('id', 'Unknown ID')} - {video.get('title', 'Unknown Title')}")
                # Ensure video has all required fields
                if 'id' not in video or 'title' not in video or 'published_at' not in video:
                    logger.error(f"Video data missing required fields: {video}")
                    continue
                if 'title' not in video or not video['title']:
                    logger.warning(f"Video {video.get('id', 'Unknown ID')} has no title. Skipping.")
                    continue
                    
                # Convert published_at from YYYYMMDD to ISO format
                try:
                    published_at_iso = datetime.strptime(video['published_at'], '%Y%m%d').isoformat()
                except ValueError:
                    published_at_iso = datetime.now().isoformat() # Fallback if format is unexpected
                video['published_at'] = published_at_iso
                video['channel_id'] = channel_id  # Add channel_id to video data

                if await db_manager.is_video_processed(video['id']):
                    logger.info(f"Video {video['id']} already processed. Skipping.")
                    continue

                logger.info(f"Processing video: {video.get('title', 'Unknown Title')}")

                # Create a temporary directory for raw subtitles
                temp_subtitle_dir = Path(f"channel_manager/downloads/{channel_id}/raw_subtitles")
                temp_subtitle_dir.mkdir(parents=True, exist_ok=True)

                # Fix: await the download_subtitles method
                raw_subtitle_path = await subtitle_downloader.download_subtitles(
                    video['id'], subtitle_preferences, str(temp_subtitle_dir)
                )

                cleaned_subtitles = ""
                if raw_subtitle_path and Path(raw_subtitle_path).exists():
                    cleaned_subtitles = subtitle_cleaner.process_subtitle_file(raw_subtitle_path)
                    # Clean up raw subtitle file after processing
                    try:
                        os.remove(raw_subtitle_path)
                    except Exception as e:
                        logger.warning(f"Could not remove raw subtitle file {raw_subtitle_path}: {e}")
                else:
                    logger.warning(f"No raw subtitles downloaded for video {video['id']}. Cannot clean.")

                # Generate summary using LLM
                generated_summary = await llm_summarizer.summarize(cleaned_subtitles)
                logger.info(f"Generated summary for video {video.get('id', 'Unknown')}: {generated_summary}")

                video['raw_subtitles'] = cleaned_subtitles
                video['cleaned_subtitles'] = cleaned_subtitles
                video['summary'] = generated_summary # Store the generated summary

                logger.debug(f"Video object before add_video: {video}")
                await db_manager.add_video(video)
                logger.info(f"Video {video['id']} added to database.")

                # Send Telegram notification with better error handling for special characters
                logger.debug(f"Video data before Telegram notification: {video}")
                try:
                    video_title = video.get('title', 'Unknown Title')
                    message = f"New video from {channel_name}: {video_title}\n\nSummary: {generated_summary}\nLink: https://www.youtube.com/watch?v={video['id']}"
                    
                    # Try sending with MarkdownV2 first
                    # Escape special characters for MarkdownV2
                    message = f"New video from {channel_name}: {video_title}\n\nSummary: {generated_summary}\nLink: https://www.youtube.com/watch?v={video['id']}"
                    
                    # Try sending with MarkdownV2
                    escaped_message = escape_markdown(message)
                    await telegram_notifier.send_message(escaped_message, parse_mode="MarkdownV2")
                except Exception as markdown_error:
                    logger.warning(f"Failed to send message with MarkdownV2, trying without formatting: {markdown_error}")
                    # Try without formatting
                    plain_message = f"New video from {channel_name}: {video_title}\n\nSummary: {generated_summary}\nLink: https://www.youtube.com/watch?v={video['id']}"
                    await telegram_notifier.send_message(plain_message, parse_mode=None)
                    
                processed_count += 1

            await db_manager.update_last_check(channel_id, datetime.now().isoformat())
            logger.info(f"Finished processing channel: {channel_name} ({processed_count} new videos)")
            return True
            
    except Exception as e:
        logger.error(f"Error processing channel {config.get('name', 'Unknown')}: {e}")
        return False

async def main():
    config_files = find_channel_configs()
    if not config_files:
        logger.warning("No channel configuration files found. Exiting.")
        return

    logger.info(f"Found {len(config_files)} channel configuration files: {config_files}")
    
    results = []
    for config_file in config_files:
        try:
            logger.info(f"Loading configuration from {config_file}")
            config = load_config(config_file)
            success = await process_channel(config)
            results.append((config_file, success))
        except Exception as e:
            logger.error(f"Error processing config file {config_file}: {e}")
            results.append((config_file, False))

    # Log summary
    successful_channels = [cfg for cfg, success in results if success]
    failed_channels = [cfg for cfg, success in results if not success]
    
    logger.info(f"Processing complete. Successful: {len(successful_channels)}, Failed: {len(failed_channels)}")
    
    if failed_channels:
        logger.error(f"Failed channels: {failed_channels}")
    if successful_channels:
        logger.info(f"Successful channels: {successful_channels}")

if __name__ == "__main__":
    # Load environment variables from .env file at the project root
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(main())
