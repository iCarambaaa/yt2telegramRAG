#!/usr/bin/env python3
"""
yt-dlp Debug Script for YouTube to Telegram Bot

This script provides comprehensive debugging tools for yt-dlp issues.
Usage: python debug_ytdlp.py <video_id_or_url> [options]
"""

import argparse
import sys
import os
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from yt2telegram.services.youtube_service import YouTubeService
from yt2telegram.utils.logging_config import LoggerFactory

logger = LoggerFactory.create_logger(__name__)

def extract_video_id(url_or_id: str) -> str:
    """Extract video ID from YouTube URL or return as-is if already an ID"""
    if "youtube.com/watch?v=" in url_or_id:
        return url_or_id.split("v=")[1].split("&")[0]
    elif "youtu.be/" in url_or_id:
        return url_or_id.split("youtu.be/")[1].split("?")[0]
    else:
        return url_or_id

def run_basic_debug(video_id: str, cookies_file: str = None):
    """Run basic yt-dlp debugging"""
    print(f"\n🔍 Basic Debug for Video ID: {video_id}")
    print("=" * 50)
    
    service = YouTubeService(cookies_file=cookies_file, debug_mode=True)
    debug_results = service.debug_video_access(video_id)
    
    print(f"\n📊 Debug Results:")
    print(json.dumps(debug_results, indent=2))
    
    return debug_results

def run_manual_ytdlp_tests(video_id: str, cookies_file: str = None):
    """Run manual yt-dlp command tests"""
    print(f"\n🛠️  Manual yt-dlp Tests for Video ID: {video_id}")
    print("=" * 50)
    
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    
    # Test commands to run
    test_commands = [
        # Basic verbose test
        f"yt-dlp -vU {video_url}",
        
        # Format listing
        f"yt-dlp -F {video_url}",
        
        # Subtitle listing
        f"yt-dlp --list-subs {video_url}",
        
        # With cookies (if provided)
        f"yt-dlp --cookies-from-browser chrome {video_url}" if not cookies_file else f"yt-dlp --cookies {cookies_file} {video_url}",
        
        # Different client tests
        f"yt-dlp --extractor-args 'youtube:player_client=mweb' {video_url}",
        f"yt-dlp --extractor-args 'youtube:player_client=tv' {video_url}",
        
        # Debug with page dumping
        f"yt-dlp --write-pages --skip-download {video_url}",
        
        # PO Token debugging
        f"yt-dlp -v --extractor-args 'youtube:pot_trace=true' {video_url}",
    ]
    
    print("🚀 Recommended test commands to run manually:")
    for i, cmd in enumerate(test_commands, 1):
        print(f"{i:2d}. {cmd}")
    
    print(f"\n💡 Pro Tips:")
    print("- Run commands one by one to isolate issues")
    print("- Check .dump files if --write-pages is used")
    print("- Look for rate limiting messages in verbose output")
    print("- Try different --sleep-interval values if rate limited")

def run_channel_debug(channel_id: str, cookies_file: str = None):
    """Debug channel access issues"""
    print(f"\n📺 Channel Debug for Channel ID: {channel_id}")
    print("=" * 50)
    
    service = YouTubeService(cookies_file=cookies_file, debug_mode=True)
    
    try:
        videos = service.get_latest_videos(channel_id, max_results=3)
        print(f"✅ Successfully fetched {len(videos)} videos from channel")
        for video in videos:
            print(f"  - {video.title} ({video.id})")
    except Exception as e:
        print(f"❌ Failed to fetch videos from channel: {e}")
        
        # Analyze the error
        analysis = service.analyze_error(e)
        print(f"\n🔍 Error Analysis:")
        print(f"Type: {analysis['error_type']}")
        print(f"Suggestions:")
        for suggestion in analysis['suggestions']:
            print(f"  - {suggestion}")
        print(f"Debug Commands:")
        for cmd in analysis['debug_commands']:
            print(f"  - {cmd}")

def main():
    parser = argparse.ArgumentParser(description="Debug yt-dlp issues for YouTube to Telegram bot")
    parser.add_argument("target", help="Video ID/URL or Channel ID to debug")
    parser.add_argument("--cookies", help="Path to cookies file")
    parser.add_argument("--channel", action="store_true", help="Debug channel instead of video")
    parser.add_argument("--manual-only", action="store_true", help="Only show manual test commands")
    
    args = parser.parse_args()
    
    print("🐛 yt-dlp Debug Tool for YouTube to Telegram Bot")
    print("=" * 60)
    
    if args.channel:
        run_channel_debug(args.target, args.cookies)
    else:
        video_id = extract_video_id(args.target)
        
        if not args.manual_only:
            run_basic_debug(video_id, args.cookies)
        
        run_manual_ytdlp_tests(video_id, args.cookies)
    
    print(f"\n📚 Additional Resources:")
    print("- yt-dlp FAQ: https://github.com/yt-dlp/yt-dlp/wiki/FAQ")
    print("- YouTube Extractor Guide: https://github.com/yt-dlp/yt-dlp/wiki/Extractors#youtube")
    print("- PO Token Guide: https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide")

if __name__ == "__main__":
    main()