#!/usr/bin/env python3
"""
Simplified YouTube to Telegram Channel Manager
Sequential processing for better reliability and easier debugging
"""

import os
import logging
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from .utils.logging_config import setup_logging
from .models.channel import ChannelConfig
from .models.video import Video
from .services.youtube_service import YouTubeService
from .services.database_service import DatabaseService
from .services.telegram_service import TelegramService
from .services.llm_service import LLMService
from .utils.subtitle_cleaner import SubtitleCleaner
from .config_finder import find_channel_configs

# Setup logging
logger = setup_logging()



def process_channel(config: ChannelConfig) -> bool:
    """Process a single channel - sequential, simple, reliable"""
    try:
        logger.info(f"Processing channel: {config.name} (ID: {config.channel_id})")

        # Initialize services
        db_service = DatabaseService(config.db_path)
        youtube_service = YouTubeService(
            cookies_file=config.cookies_file,
            retry_attempts=config.retry_attempts,
            retry_delay_seconds=config.retry_delay_seconds
        )
        telegram_service = TelegramService(bot_configs=config.telegram_bots_config)
        llm_service = LLMService(llm_config=config.llm_config)
        subtitle_cleaner = SubtitleCleaner()



        # Get latest videos
        logger.info(f"Fetching latest {config.max_videos_to_fetch} videos")
        videos = youtube_service.get_latest_videos(
            config.channel_id, 
            config.max_videos_to_fetch
        )

        processed_count = 0
        for video in videos:
            logger.info(f"Processing video: {video.title}")

            # Skip if already processed
            if db_service.is_video_processed(video.id):
                logger.info(f"Video {video.id} already processed, skipping")
                continue

            # No need to handle published_at - we use processed_at from database

            # Download and clean subtitles
            temp_subtitle_dir = Path(f"yt2telegram/downloads/{config.channel_id}/raw_subtitles")
            raw_subtitle_path = youtube_service.download_subtitles(
                video.id, 
                config.subtitle_preferences, 
                str(temp_subtitle_dir)
            )

            # Process subtitles with enhanced cleaning
            raw_subtitles = ""
            cleaned_subtitles = ""
            
            if raw_subtitle_path and Path(raw_subtitle_path).exists():
                # Read raw subtitles
                with open(raw_subtitle_path, 'r', encoding='utf-8') as f:
                    raw_subtitles = f.read()
                
                # Clean subtitles with basic VTT cleaning
                cleaned_subtitles = subtitle_cleaner.process_subtitle_file(raw_subtitle_path)
                
                # Clean up raw subtitle file
                try:
                    os.remove(raw_subtitle_path)
                except Exception as e:
                    logger.warning(f"Could not remove raw subtitle file: {e}")
            else:
                logger.warning(f"No subtitles downloaded for video {video.id}")

            # Generate summary
            summary = ""
            if cleaned_subtitles:
                try:
                    summary = llm_service.summarize(cleaned_subtitles)
                except Exception as e:
                    logger.error(f"Failed to generate summary: {e}")
                    summary = "Summary generation failed"

            # Update video with processed data
            video.raw_subtitles = raw_subtitles
            video.cleaned_subtitles = cleaned_subtitles
            video.summary = summary

            # Save to database
            db_service.add_video(video)

            # Send Telegram notification with proper formatting
            if summary:
                try:
                    # Determine channel type for formatting
                    channel_type = "default"
                    if "isaac" in config.name.lower() or "arthur" in config.name.lower():
                        channel_type = "isaac_arthur"
                    elif "robyn" in config.name.lower():
                        channel_type = "robynhd"
                    
                    telegram_service.send_video_notification(
                        config.name,
                        video.title,
                        video.id,
                        summary,
                        channel_type
                    )
                except Exception as e:
                    logger.error(f"Failed to send Telegram notification: {e}")

            processed_count += 1
            logger.info(f"Successfully processed video: {video.title}")

        # Update last check timestamp
        db_service.update_last_check(config.channel_id, datetime.now().isoformat())
        
        logger.info(f"Finished processing channel: {config.name} ({processed_count} new videos)")
        return True

    except Exception as e:
        logger.error(f"Error processing channel {config.name}: {e}", exc_info=True)
        return False

def main():
    """Main entry point"""
    # Load environment variables
    load_dotenv()
    
    # Find channel configuration files
    config_files = find_channel_configs()
    if not config_files:
        logger.warning("No channel configuration files found")
        return

    logger.info(f"Found {len(config_files)} channel configuration files")
    
    # Process each channel with 5-second sleep between them
    results = []
    for i, config_file in enumerate(config_files):
        try:
            logger.info(f"Loading configuration from {config_file}")
            config = ChannelConfig.from_yaml(config_file)
            success = process_channel(config)
            results.append((config_file, success))
            
            # Sleep 5 seconds between channels (except after the last one)
            if i < len(config_files) - 1:
                logger.info("Waiting 5 seconds before processing next channel...")
                time.sleep(5)
                
        except Exception as e:
            logger.error(f"Error processing config file {config_file}: {e}", exc_info=True)
            results.append((config_file, False))

    # Log summary
    successful = [cfg for cfg, success in results if success]
    failed = [cfg for cfg, success in results if not success]
    
    logger.info(f"Processing complete. Successful: {len(successful)}, Failed: {len(failed)}")
    
    if failed:
        logger.error(f"Failed channels: {failed}")
    if successful:
        logger.info(f"Successful channels: {successful}")

if __name__ == "__main__":
    main()