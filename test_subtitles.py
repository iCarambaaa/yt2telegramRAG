#!/usr/bin/env python3
"""
YouTube Subtitle Testing Script
================================
This script tests subtitle extraction capabilities for a specific YouTube video.
It lists all available subtitles (manual and auto-generated) and downloads them.

Usage:
    python test_subtitles.py [VIDEO_ID]
    
Example:
    python test_subtitles.py IE1E9m5u488
"""

import os
import sys
import json
import tempfile
import logging
from typing import Dict, List, Optional, Tuple
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("subtitle_test.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

class SubtitleTester:
    """Comprehensive subtitle testing and extraction class."""
    
    def __init__(self, cookies_file: Optional[str] = None):
        """Initialize the subtitle tester."""
        self.cookies_file = cookies_file
        self.temp_dir = tempfile.gettempdir()
        logging.info(f"Initialized SubtitleTester with temp_dir: {self.temp_dir}")
        if cookies_file:
            logging.info(f"Using cookies file: {cookies_file}")
    
    def get_video_info(self, video_id: str) -> Dict:
        """Get comprehensive video information including available subtitles."""
        logging.info(f"Getting video info for: {video_id}")
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'skip_download': True,
        }
        
        if self.cookies_file and os.path.exists(self.cookies_file):
            ydl_opts['cookiefile'] = self.cookies_file
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
                
                # Extract relevant information
                video_info = {
                    'id': info.get('id'),
                    'title': info.get('title'),
                    'uploader': info.get('uploader'),
                    'duration': info.get('duration'),
                    'upload_date': info.get('upload_date'),
                    'view_count': info.get('view_count'),
                    'description': info.get('description'),
                    'subtitles': info.get('subtitles', {}),
                    'automatic_captions': info.get('automatic_captions', {}),
                }
                
                logging.info(f"Video info retrieved: {video_info['title']}")
                logging.debug(f"Raw subtitles data: {json.dumps(video_info['subtitles'], indent=2)}")
                logging.debug(f"Raw auto-captions data: {json.dumps(video_info['automatic_captions'], indent=2)}")
                
                return video_info
                
        except Exception as e:
            logging.error(f"Error getting video info: {e}")
            raise
    
    def list_available_subtitles(self, video_id: str) -> Dict[str, List[str]]:
        """List all available subtitle languages and types."""
        logging.info(f"Listing available subtitles for: {video_id}")
        
        try:
            # Method 1: Using yt-dlp
            video_info = self.get_video_info(video_id)
            
            available_subs = {
                'manual_subtitles': [],
                'auto_subtitles': [],
                'yt_dlp_subtitles': list(video_info['subtitles'].keys()),
                'yt_dlp_auto_captions': list(video_info['automatic_captions'].keys())
            }
            
            # Method 2: Using YouTubeTranscriptApi for additional info
            try:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                
                for transcript in transcript_list:
                    if transcript.is_generated:
                        available_subs['auto_subtitles'].append(
                            f"{transcript.language} ({transcript.language_code})"
                        )
                    else:
                        available_subs['manual_subtitles'].append(
                            f"{transcript.language} ({transcript.language_code})"
                        )
                        
            except (TranscriptsDisabled, NoTranscriptFound) as e:
                logging.warning(f"YouTubeTranscriptApi error: {e}")
            
            logging.info("Available subtitle languages:")
            logging.info(f"  Manual subtitles: {available_subs['manual_subtitles']}")
            logging.info(f"  Auto subtitles: {available_subs['auto_subtitles']}")
            logging.info(f"  yt-dlp manual: {available_subs['yt_dlp_subtitles']}")
            logging.info(f"  yt-dlp auto: {available_subs['yt_dlp_auto_captions']}")
            
            return available_subs
            
        except Exception as e:
            logging.error(f"Error listing subtitles: {e}")
            raise
    
    def download_subtitle_yt_dlp(self, video_id: str, language: str, auto: bool = False) -> Optional[str]:
        """Download subtitles using yt-dlp."""
        logging.info(f"Downloading {'auto-' if auto else ''}subtitles for {video_id} in {language}")
        
        subtitle_type = "automatic captions" if auto else "subtitles"
        
        ydl_opts = {
            'skip_download': True,
            'outtmpl': os.path.join(self.temp_dir, f"{video_id}_%(ext)s"),
            'quiet': True,
        }
        
        if auto:
            ydl_opts['writeautomaticsub'] = True
            ydl_opts['subtitleslangs'] = [language]
        else:
            ydl_opts['writesubtitles'] = True
            ydl_opts['subtitleslangs'] = [language]
        
        if self.cookies_file and os.path.exists(self.cookies_file):
            ydl_opts['cookiefile'] = self.cookies_file
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
            
            # Find the downloaded subtitle file
            extensions = ['vtt', 'srt', 'srv1', 'srv2', 'srv3']
            for ext in extensions:
                filename = f"{video_id}.{language}.{ext}"
                filepath = os.path.join(self.temp_dir, filename)
                
                if os.path.exists(filepath):
                    logging.info(f"Found {subtitle_type} file: {filepath}")
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Clean up
                        os.remove(filepath)
                        logging.info(f"Successfully read {subtitle_type} content ({len(content)} chars)")
                        return content
                    except Exception as e:
                        logging.error(f"Error reading {subtitle_type} file: {e}")
                        if os.path.exists(filepath):
                            os.remove(filepath)
        
        except Exception as e:
            logging.error(f"Error downloading {subtitle_type} with yt-dlp: {e}")
        
        return None
    
    def download_subtitle_transcript_api(self, video_id: str, language: str, auto: bool = False) -> Optional[List[Dict]]:
        """Download subtitles using YouTubeTranscriptApi."""
        logging.info(f"Downloading transcript via API for {video_id} in {language}")
        
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Try to find the requested transcript
            for transcript in transcript_list:
                if transcript.language_code == language:
                    if auto and transcript.is_generated:
                        transcript_data = transcript.fetch()
                        logging.info(f"Successfully fetched auto-generated transcript ({len(transcript_data)} segments)")
                        return transcript_data
                    elif not auto and not transcript.is_generated:
                        transcript_data = transcript.fetch()
                        logging.info(f"Successfully fetched manual transcript ({len(transcript_data)} segments)")
                        return transcript_data
            
            logging.warning(f"Requested transcript not found: {language} (auto: {auto})")
            return None
            
        except (TranscriptsDisabled, NoTranscriptFound) as e:
            logging.error(f"Transcript API error: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error with transcript API: {e}")
            return None
    
    def test_all_subtitles(self, video_id: str) -> Dict:
        """Comprehensive test of all subtitle extraction methods."""
        logging.info("=" * 80)
        logging.info(f"STARTING COMPREHENSIVE SUBTITLE TEST FOR VIDEO: {video_id}")
        logging.info("=" * 80)
        
        results = {
            'video_id': video_id,
            'video_info': None,
            'available_subtitles': None,
            'downloaded_subtitles': {},
            'errors': []
        }
        
        try:
            # Step 1: Get video information
            logging.info("\n--- STEP 1: Video Information ---")
            video_info = self.get_video_info(video_id)
            results['video_info'] = video_info
            
            # Step 2: List available subtitles
            logging.info("\n--- STEP 2: Available Subtitles ---")
            available = self.list_available_subtitles(video_id)
            results['available_subtitles'] = available
            
            # Step 3: Download subtitles using different methods
            logging.info("\n--- STEP 3: Subtitle Downloads ---")
            
            # Download manual subtitles
            for lang in available['yt_dlp_subtitles']:
                logging.info(f"\nAttempting to download manual subtitles for: {lang}")
                content = self.download_subtitle_yt_dlp(video_id, lang, auto=False)
                if content:
                    results['downloaded_subtitles'][f"manual_{lang}"] = {
                        'method': 'yt-dlp',
                        'language': lang,
                        'type': 'manual',
                        'content_length': len(content),
                        'preview': content[:200] + "..." if len(content) > 200 else content
                    }
            
            # Download auto-generated subtitles
            for lang in available['yt_dlp_auto_captions']:
                logging.info(f"\nAttempting to download auto-generated subtitles for: {lang}")
                content = self.download_subtitle_yt_dlp(video_id, lang, auto=True)
                if content:
                    results['downloaded_subtitles'][f"auto_{lang}"] = {
                        'method': 'yt-dlp',
                        'language': lang,
                        'type': 'auto',
                        'content_length': len(content),
                        'preview': content[:200] + "..." if len(content) > 200 else content
                    }
            
            # Try YouTubeTranscriptApi for additional transcripts
            logging.info("\n--- STEP 4: YouTubeTranscriptApi Downloads ---")
            try:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                
                for transcript in transcript_list:
                    lang_code = transcript.language_code
                    transcript_type = "auto" if transcript.is_generated else "manual"
                    
                    logging.info(f"\nDownloading via API: {lang_code} ({transcript_type})")
                    transcript_data = transcript.fetch()
                    
                    if transcript_data:
                        # Convert to text format
                        text_content = "\n".join([entry['text'] for entry in transcript_data])
                        
                        results['downloaded_subtitles'][f"api_{transcript_type}_{lang_code}"] = {
                            'method': 'YouTubeTranscriptApi',
                            'language': lang_code,
                            'type': transcript_type,
                            'content_length': len(text_content),
                            'segments': len(transcript_data),
                            'preview': text_content[:200] + "..." if len(text_content) > 200 else text_content
                        }
                        
            except Exception as e:
                logging.error(f"YouTubeTranscriptApi error: {e}")
                results['errors'].append(str(e))
            
            # Summary
            logging.info("\n" + "=" * 80)
            logging.info("SUBTITLE TEST SUMMARY")
            logging.info("=" * 80)
            logging.info(f"Video: {video_info['title']}")
            logging.info(f"Total subtitle sources found: {len(results['downloaded_subtitles'])}")
            
            for key, subtitle_info in results['downloaded_subtitles'].items():
                logging.info(f"  {key}: {subtitle_info['content_length']} chars "
                           f"({subtitle_info['method']}, {subtitle_info['type']})")
            
            if results['errors']:
                logging.error(f"Errors encountered: {results['errors']}")
            
            return results
            
        except Exception as e:
            logging.error(f"Critical error during subtitle testing: {e}")
            results['errors'].append(str(e))
            return results

def main():
    """Main function to run subtitle tests."""
    load_dotenv()
    
    # Get video ID from command line or use default
    video_id = sys.argv[1] if len(sys.argv) > 1 else "IE1E9m5u488"
    
    # Get cookies file from environment
    cookies_file = os.getenv("COOKIES_FILE")
    
    # Initialize tester
    tester = SubtitleTester(cookies_file=cookies_file)
    
    # Run comprehensive test
    results = tester.test_all_subtitles(video_id)
    
    # Save results to JSON file
    output_file = f"subtitle_test_results_{video_id}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logging.info(f"\nResults saved to: {output_file}")
    
    # Print summary to console
    print("\n" + "=" * 80)
    print("SUBTITLE TEST COMPLETED")
    print("=" * 80)
    print(f"Video ID: {video_id}")
    print(f"Video Title: {results['video_info']['title'] if results['video_info'] else 'Unknown'}")
    print(f"Total subtitle sources: {len(results['downloaded_subtitles'])}")
    print(f"Results saved to: {output_file}")
    
    if results['errors']:
        print(f"Errors: {len(results['errors'])}")
        for error in results['errors']:
            print(f"  - {error}")

if __name__ == "__main__":
    main()