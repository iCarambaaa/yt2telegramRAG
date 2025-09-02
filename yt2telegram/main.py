#!/usr/bin/env python3
"""
Simplified YouTube to Telegram Channel Manager
Sequential processing for better reliability and easier debugging
"""

import os
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from .utils.logging_config import setup_logging, LoggerFactory
from .models.channel import ChannelConfig
from .models.video import Video
from .services.youtube_service import YouTubeService
from .services.database_service import DatabaseService
from .services.telegram_service import TelegramService
from .services.llm_service import LLMService
from .services.multi_model_llm_service import MultiModelLLMService
from .utils.subtitle_cleaner import SubtitleCleaner
from .config_finder import find_channel_configs

# Setup logging
setup_logging()
logger = LoggerFactory.create_logger(__name__)



def process_channel(config: ChannelConfig) -> bool:
    """Process a single channel - sequential, simple, reliable"""
    try:
        logger.info("Processing channel", channel_name=config.name, channel_id=config.channel_id)

        # Initialize services
        db_service = DatabaseService(config.db_path)
        youtube_service = YouTubeService(
            cookies_file=config.cookies_file,
            retry_attempts=config.retry_attempts,
            retry_delay_seconds=config.retry_delay_seconds
        )
        telegram_service = TelegramService(bot_configs=config.telegram_bots_config)
        
        # Initialize appropriate LLM service based on configuration
        multi_model_config = config.llm_config.get('multi_model', {})
        if multi_model_config.get('enabled', False):
            logger.info("Initializing multi-model LLM service", 
                       primary_model=multi_model_config.get('primary_model'),
                       secondary_model=multi_model_config.get('secondary_model'),
                       synthesis_model=multi_model_config.get('synthesis_model'))
            llm_service = MultiModelLLMService(llm_config=config.llm_config, channel_name=config.name)
        else:
            logger.info("Initializing single-model LLM service", 
                       model=config.llm_config.get('llm_model'))
            llm_service = LLMService(llm_config=config.llm_config)
        
        subtitle_cleaner = SubtitleCleaner()



        # Get latest videos
        logger.info("Fetching latest videos", max_videos=config.max_videos_to_fetch)
        videos = youtube_service.get_latest_videos(
            config.channel_id, 
            config.max_videos_to_fetch
        )

        processed_count = 0
        successful_count = 0
        failed_count = 0
        
        for video in videos:
            logger.info("Processing video", video_id=video.id, video_title=video.title, published_date=video.published_at)

            # Skip if already processed
            if db_service.is_video_processed(video.id):
                logger.info("Video already processed, skipping", video_id=video.id)
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
                    logger.warning("Could not remove raw subtitle file", error=str(e), file_path=raw_subtitle_path)
                
                logger.info("Successfully processed subtitles", 
                           video_id=video.id, 
                           raw_size=len(raw_subtitles), 
                           cleaned_size=len(cleaned_subtitles),
                           compression_ratio=f"{(1 - len(cleaned_subtitles)/len(raw_subtitles))*100:.1f}%" if raw_subtitles else "N/A")
            else:
                logger.warning("No subtitles downloaded for video - may be age-restricted or region-blocked", video_id=video.id)

            # Generate summary
            summary = ""
            if cleaned_subtitles:
                try:
                    logger.info("Generating summary", video_id=video.id, subtitle_length=len(cleaned_subtitles))
                    
                    # Check if using multi-model service
                    if hasattr(llm_service, 'summarize_enhanced'):
                        # Multi-model service - get enhanced results
                        summary_result = llm_service.summarize_enhanced(cleaned_subtitles)
                        summary = summary_result.get('final_summary', '')
                        
                        # Populate multi-model fields
                        video.summarization_method = summary_result.get('summarization_method', 'multi_model')
                        video.primary_summary = summary_result.get('primary_summary')
                        video.secondary_summary = summary_result.get('secondary_summary')
                        video.synthesis_summary = summary_result.get('synthesis_summary')
                        video.primary_model = summary_result.get('primary_model')
                        video.secondary_model = summary_result.get('secondary_model')
                        video.synthesis_model = summary_result.get('synthesis_model')
                        video.processing_time_seconds = summary_result.get('processing_time_seconds')
                        video.fallback_used = summary_result.get('fallback_used', False)
                        video.token_usage_json = summary_result.get('token_usage_json', '{}')
                        video.cost_estimate = summary_result.get('cost_estimate', 0.0)
                    else:
                        # Single-model service
                        summary = llm_service.summarize(cleaned_subtitles)
                        video.summarization_method = 'single_model'
                    
                    logger.info("Successfully generated summary", video_id=video.id, summary_length=len(summary))
                except Exception as e:
                    logger.error("Failed to generate summary", error=str(e), video_id=video.id)
                    summary = "Summary generation failed"
                    video.summarization_method = 'failed'
            else:
                logger.warning("No subtitles available for summary generation", video_id=video.id)

            # Update video with processed data
            video.raw_subtitles = raw_subtitles
            video.cleaned_subtitles = cleaned_subtitles
            video.summary = summary

            # Save to database
            db_service.add_video(video)

            # Send Telegram notification with proper formatting
            telegram_success = False
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
                        channel_type,
                        video.published_at
                    )
                    telegram_success = True
                    logger.info("Successfully sent Telegram notification", video_id=video.id)
                except Exception as e:
                    logger.error("Failed to send Telegram notification", error=str(e), video_id=video.id)
                    telegram_success = False
            else:
                logger.warning("No summary available, skipping Telegram notification", video_id=video.id)

            processed_count += 1
            if telegram_success:
                successful_count += 1
                logger.info("Successfully processed and sent video", video_id=video.id, video_title=video.title)
            else:
                failed_count += 1
                logger.error("Processed video but failed to send notification", video_id=video.id, video_title=video.title)

        # Update last check timestamp
        db_service.update_last_check(config.channel_id, datetime.now().isoformat())
        
        logger.info("Finished processing channel", channel_name=config.name, processed_count=processed_count, successful_notifications=successful_count, failed_notifications=failed_count)
        return successful_count > 0 or processed_count == 0  # Success if we sent notifications or had nothing to process

    except Exception as e:
        logger.error("Error processing channel", channel_name=config.name, error=str(e))
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

    logger.info("Found channel configuration files", count=len(config_files))
    
    # Process each channel with 5-second sleep between them
    results = []
    for i, config_file in enumerate(config_files):
        try:
            logger.info("Loading configuration", config_file=config_file)
            config = ChannelConfig.from_yaml(config_file)
            success = process_channel(config)
            results.append((config_file, success))
            
            # Sleep 5 seconds between channels (except after the last one)
            if i < len(config_files) - 1:
                logger.info("Waiting 5 seconds before processing next channel...")
                time.sleep(5)
                
        except Exception as e:
            logger.error("Error processing config file", config_file=config_file, error=str(e))
            results.append((config_file, False))

    # Log summary
    successful = [cfg for cfg, success in results if success]
    failed = [cfg for cfg, success in results if not success]
    
    logger.info("Processing complete", successful_count=len(successful), failed_count=len(failed))
    
    if failed:
        logger.error("Failed channels", failed_channels=failed)
    if successful:
        logger.info("Successful channels", successful_channels=successful)

if __name__ == "__main__":
    main()