#!/usr/bin/env python3
"""
Entry point for the YouTube2Telegram RAG package.
This module provides the main CLI interface for the application.
"""

import argparse
import logging
import sys
from pathlib import Path

# Add the src directory to the path for development
sys.path.insert(0, str(Path(__file__).parent.parent))

from yt2telegram.core.youtube2telegram import main as youtube_monitor_main
from yt2telegram.bot.tg_bot import TelegramBot
from yt2telegram.db.database import DatabaseManager

def setup_logging(verbose: bool = False):
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('youtube_telegram.log')
        ]
    )

def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(
        description='YouTube2Telegram RAG - Monitor YouTube channels and send summaries to Telegram'
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        default='config.json',
        help='Configuration file path (default: config.json)'
    )
    
    parser.add_argument(
        '--monitor',
        action='store_true',
        help='Start the YouTube monitoring service'
    )
    
    parser.add_argument(
        '--bot',
        action='store_true',
        help='Start the Telegram bot for Q&A'
    )
    
    parser.add_argument(
        '--test',
        action='store_true',
        help='Run basic functionality tests'
    )
    
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show database statistics'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    if args.test:
        logger.info("Running basic functionality tests...")
        
        # Run basic import tests
        success = True
        
        try:
            # Test core imports
            from yt2telegram.core.youtube2telegram import main as youtube_monitor_main
            from yt2telegram.bot.tg_bot import TelegramBot
            from yt2telegram.db.database import DatabaseManager
            from yt2telegram.utils.extract_clean_subtitles import SubtitleExtractor
            from yt2telegram.utils.subtitle_downloader import AdvancedSubtitleDownloader
            
            logger.info("✓ All core modules imported successfully")
            
            # Test database functionality
            test_db = DatabaseManager()
            logger.info("✓ Database manager initialized successfully")
            
            # Test basic functionality
            test_video_id = "test123"
            test_channel = "test_channel"
            test_title = "Test Video"
            
            # Test database operations
            test_video_data = {
                'video_id': test_video_id,
                'channel_id': test_channel,
                'title': test_title,
                'published_at': '2024-01-01T00:00:00Z',
                'description': 'Test video description'
            }
            
            success_add = test_db.add_video(test_video_data)
            is_processed = test_db.get_video_by_id(test_video_id) is not None
            
            if success_add and is_processed:
                logger.info("✓ Database operations working correctly")
            else:
                logger.error("✗ Database operations failed")
                success = False
                
            # Clean up test data
            test_db.execute_query(
                "DELETE FROM processed_videos WHERE video_id = ?",
                (test_video_id,)
            )
            logger.info("✓ Test data cleaned up")
            
        except Exception as e:
            logger.error(f"✗ Test failed: {e}")
            success = False
            
        if success:
            logger.info("All tests passed!")
            return 0
        else:
            logger.error("Some tests failed!")
            return 1
    
    if args.stats:
        logger.info("Fetching database statistics...")
        stats = db.get_stats()
        
        print("\n" + "="*50)
        print("DATABASE STATISTICS")
        print("="*50)
        print(f"Total videos processed: {stats.get('total_videos', 0)}")
        print(f"Active channels: {stats.get('active_channels', 0)}")
        print(f"Total subtitles: {stats.get('total_subtitles', 0)}")
        
        latest = stats.get('latest_video')
        if latest:
            print(f"Latest video: {latest.get('title', 'N/A')}")
            print(f"Published: {latest.get('published_at', 'N/A')}")
        print("="*50)
        
        return 0
    
    if args.monitor:
        logger.info("Starting YouTube monitoring service...")
        try:
            youtube_monitor_main()
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
        except Exception as e:
            logger.error(f"Error in monitoring service: {e}")
            return 1
            
    elif args.bot:
        logger.info("Starting Telegram bot...")
        try:
            bot = TelegramBot()
            bot.run()
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Error in Telegram bot: {e}")
            return 1
            
    else:
        # Default behavior: show help
        parser.print_help()
        print("\nExamples:")
        print("  python -m yt2telegram --monitor    # Start monitoring")
        print("  python -m yt2telegram --bot        # Start Telegram bot")
        print("  python -m yt2telegram --test       # Run tests")
        print("  python -m yt2telegram --stats      # Show statistics")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())