#!/usr/bin/env python3
"""
Test script to verify all imports work correctly after reorganization
"""

import sys
import os
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

def test_imports():
    """Test that all modules can be imported correctly"""
    print("Testing imports...")
    
    try:
        from yt2telegram.core.youtube2telegram import main as youtube_monitor_main
        print("✅ Successfully imported youtube_monitor_main")
    except ImportError as e:
        print(f"❌ Failed to import youtube_monitor_main: {e}")
        return False
    
    try:
        from yt2telegram.bot.tg_bot import TelegramBot
        print("✅ Successfully imported TelegramBot")
    except ImportError as e:
        print(f"❌ Failed to import TelegramBot: {e}")
        return False
    
    try:
        from yt2telegram.utils.extract_clean_subtitles import SubtitleExtractor
        print("✅ Successfully imported SubtitleExtractor")
    except ImportError as e:
        print(f"❌ Failed to import SubtitleExtractor: {e}")
        return False
    
    try:
        from yt2telegram.utils.subtitle_downloader import AdvancedSubtitleDownloader
        print("✅ Successfully imported AdvancedSubtitleDownloader")
    except ImportError as e:
        print(f"❌ Failed to import AdvancedSubtitleDownloader: {e}")
        return False
    
    print("\n🎉 All imports successful!")
    return True

def test_basic_functionality():
    """Test basic functionality of the modules"""
    print("\nTesting basic functionality...")
    
    try:
        from yt2telegram.utils.extract_clean_subtitles import SubtitleExtractor
        
        # Test SubtitleExtractor initialization
        extractor = SubtitleExtractor(":memory:")
        extractor.setup_database()
        print("✅ SubtitleExtractor initialized successfully")
        
        # Test database connection
        import sqlite3
        conn = sqlite3.connect(":memory:")
        conn.close()
        print("✅ Database connection test passed")
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False
    
    print("✅ Basic functionality tests passed!")
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("YouTube2Telegram RAG - Import Test Suite")
    print("=" * 50)
    
    success = True
    
    # Test imports
    if not test_imports():
        success = False
    
    # Test basic functionality
    if not test_basic_functionality():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All tests passed! The reorganization was successful.")
    else:
        print("❌ Some tests failed. Please check the errors above.")
    print("=" * 50)