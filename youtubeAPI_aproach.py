#!/usr/bin/env python3
"""
Simple YouTube Subtitle Extractor
==============================
Extracts clean, plain text subtitles from YouTube videos without timestamps or formatting.

Usage:
    python extract_clean_subtitles.py [VIDEO_ID]
    
Example:
    python extract_clean_subtitles.py IE1E9m5u488
"""

import os
import sys
import json
import logging
from typing import List, Dict, Optional
from youtube_transcript_api import YouTubeTranscriptApi

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def extract_plain_text_subtitles(video_id: str, language: str = 'de') -> Optional[str]:
    """
    Extract plain text subtitles from a YouTube video.
    
    Args:
        video_id: YouTube video ID
        language: Language code for subtitles (default: 'de')
        
    Returns:
        Plain text of subtitles or None if failed
    """
    try:
        # Use the YouTubeTranscriptApi to get the transcript directly
        logging.info(f"Attempting to get transcript for {video_id} in {language}")
        yta = YouTubeTranscriptApi()
        transcript = yta.fetch(video_id, languages=[language])
        
        # Extract plain text from transcript
        if transcript:
            logging.info(f"Successfully fetched transcript for {video_id}")
            plain_text = ""
            for entry in transcript.snippets:
                plain_text += entry.text + " "
            
            # Clean up extra whitespace
            plain_text = " ".join(plain_text.split())
            logging.info(f"Successfully extracted {len(plain_text)} characters of subtitle text")
            return plain_text.strip()
        else:
            logging.error("No transcript data received")
            return None
            
    except Exception as e:
        logging.warning(f"Failed to get transcript in {language}: {e}")
        try:
            # Try auto-generated transcript
            logging.info(f"Attempting to get auto-generated transcript for {video_id} in {language}")
            yta = YouTubeTranscriptApi()
            transcript = yta.fetch(video_id, languages=[f'{language}-auto'])
            
            # Extract plain text from transcript
            if transcript:
                logging.info(f"Successfully fetched auto-generated transcript for {video_id}")
                plain_text = ""
                for entry in transcript.snippets:
                    plain_text += entry.text + " "
                
                # Clean up extra whitespace
                plain_text = " ".join(plain_text.split())
                logging.info(f"Successfully extracted {len(plain_text)} characters of subtitle text")
                return plain_text.strip()
            else:
                logging.error("No auto-generated transcript data received")
                return None
                
        except Exception as e2:
            logging.error(f"Failed to get auto-generated transcript: {e2}")
            # Try any available transcript
            try:
                logging.info(f"Attempting to get any available transcript for {video_id}")
                yta = YouTubeTranscriptApi()
                transcript = yta.fetch(video_id)
                
                # Extract plain text from transcript
                if transcript:
                    logging.info(f"Successfully fetched any available transcript for {video_id}")
                    plain_text = ""
                    for entry in transcript.snippets:
                        plain_text += entry.text + " "
                    
                    # Clean up extra whitespace
                    plain_text = " ".join(plain_text.split())
                    logging.info(f"Successfully extracted {len(plain_text)} characters of subtitle text")
                    return plain_text.strip()
                else:
                    logging.error("No transcript data received")
                    return None
                    
            except Exception as e3:
                logging.error(f"Failed to get any transcript: {e3}")
                return None

def save_clean_subtitles(video_id: str, text: str, output_file: str = None):
    """
    Save clean subtitles to a text file.
    
    Args:
        video_id: YouTube video ID
        text: Clean subtitle text
        output_file: Output file path (default: auto-generated)
    """
    if not output_file:
        output_file = f"clean_subtitles_{video_id}.txt"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(text)
    
    logging.info(f"Clean subtitles saved to: {output_file}")

def main():
    """Main function to extract clean subtitles."""
    # Get video ID from command line or use default
    video_id = sys.argv[1] if len(sys.argv) > 1 else "IE1E9m5u488"
    
    # Extract clean subtitles
    logging.info(f"Extracting clean subtitles for video: {video_id}")
    clean_text = extract_plain_text_subtitles(video_id)
    
    if clean_text:
        print("\n" + "=" * 80)
        print("CLEAN SUBTITLE EXTRACTION SUCCESSFUL")
        print("=" * 80)
        print(f"Video ID: {video_id}")
        print(f"Text length: {len(clean_text)} characters")
        print("\nPreview (first 500 chars):")
        print("-" * 50)
        print(clean_text[:500] + ("..." if len(clean_text) > 500 else ""))
        print("-" * 50)
        
        # Save to file
        save_clean_subtitles(video_id, clean_text)
        
        # Also save as JSON for compatibility with existing system
        json_output = {
            "video_id": video_id,
            "clean_text": clean_text,
            "text_length": len(clean_text)
        }
        
        json_file = f"clean_subtitles_{video_id}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_output, f, indent=2, ensure_ascii=False)
        
        print(f"\nFiles saved:")
        print(f"  - clean_subtitles_{video_id}.txt")
        print(f"  - clean_subtitles_{video_id}.json")
        
    else:
        print(f"\n❌ Failed to extract clean subtitles for video: {video_id}")
        sys.exit(1)

if __name__ == "__main__":
    main()
