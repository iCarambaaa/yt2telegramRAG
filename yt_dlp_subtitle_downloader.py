#!/usr/bin/env python3
"""
YouTube Subtitle and Metadata Downloader using yt-dlp
====================================================
Downloads subtitles and metadata from YouTube videos using yt-dlp.
Prioritizes original language subtitles, falls back to auto-generated if needed.

Usage:
    python yt_dlp_subtitle_downloader.py [VIDEO_ID]
    
Example:
    python yt_dlp_subtitle_downloader.py IE1E9m5u488
"""

import os
import sys
import json
import logging
import subprocess
from typing import Dict, List, Optional, Tuple
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("yt_dlp_subtitle_downloader.log")
    ]
)

class YouTubeSubtitleDownloader:
    """Handles downloading subtitles and metadata from YouTube videos using yt-dlp."""
    
    def __init__(self, output_dir: str = "downloads"):
        """
        Initialize the downloader.
        
        Args:
            output_dir: Directory to save downloaded files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
    def check_yt_dlp_installed(self) -> bool:
        """Check if yt-dlp is installed and accessible."""
        try:
            result = subprocess.run(
                ["yt-dlp", "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            logging.info(f"yt-dlp version: {result.stdout.strip()}")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            logging.error("yt-dlp not found. Please install it first:")
            logging.error("  pip install yt-dlp")
            return False
    
    def get_video_info(self, video_id: str) -> Dict:
        """
        Get comprehensive video metadata using yt-dlp.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Dictionary containing video metadata
        """
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        cmd = [
            "yt-dlp",
            "--dump-json",
            "--no-download",
            url
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                encoding='utf-8'
            )
            
            # Parse JSON output
            video_info = json.loads(result.stdout)
            logging.info(f"Retrieved metadata for: {video_info.get('title', 'Unknown')}")
            return video_info
            
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to get video info: {e}")
            logging.error(f"stderr: {e.stderr}")
            return {}
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse JSON: {e}")
            return {}
    
    def list_available_subtitles(self, video_id: str) -> Dict:
        """
        List all available subtitles for a video.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Dictionary with subtitle information
        """
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        cmd = [
            "yt-dlp",
            "--list-subs",
            "--no-download",
            url
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                encoding='utf-8'
            )
            
            # Parse subtitle listing
            subtitles = {
                "manual": {},
                "auto": {},
                "all_languages": []
            }
            
            lines = result.stdout.strip().split('\n')
            current_section = None
            
            for line in lines:
                line = line.strip()
                if "Available subtitles" in line:
                    current_section = "manual"
                elif "Available automatic captions" in line:
                    current_section = "auto"
                elif line and current_section and not line.startswith("Language"):
                    parts = line.split()
                    if len(parts) >= 2:
                        lang = parts[0]
                        formats = parts[1:] if len(parts) > 1 else []
                        subtitles[current_section][lang] = formats
                        if lang not in subtitles["all_languages"]:
                            subtitles["all_languages"].append(lang)
            
            logging.info(f"Found subtitles: {subtitles}")
            return subtitles
            
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to list subtitles: {e}")
            return {"manual": {}, "auto": {}, "all_languages": []}
    
    def download_subtitles(self, video_id: str, language: str = None) -> Tuple[bool, List[str]]:
        """
        Download subtitles for a video, prioritizing original language.
        
        Args:
            video_id: YouTube video ID
            language: Preferred language code (auto-detected if None)
            
        Returns:
            Tuple of (success, list of downloaded subtitle files)
        """
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Get video info to determine original language
        video_info = self.get_video_info(video_id)
        original_language = video_info.get('language', None)
        
        if language is None and original_language:
            language = original_language
            logging.info(f"Using original language: {language}")
        elif language is None:
            language = "en"  # Default fallback
            logging.info(f"Using default language: {language}")
        
        # List available subtitles
        subtitles = self.list_available_subtitles(video_id)
        
        # Determine which subtitles to download
        download_manual = language in subtitles["manual"]
        download_auto = language in subtitles["auto"]
        
        downloaded_files = []
        
        # Try manual subtitles first
        if download_manual:
            logging.info(f"Downloading manual subtitles for language: {language}")
            success, files = self._download_subtitles_for_type(
                video_id, language, manual=True
            )
            if success:
                downloaded_files.extend(files)
        
        # Fallback to auto-generated if manual not available
        elif download_auto:
            logging.info(f"Manual subtitles not available, downloading auto-generated for: {language}")
            success, files = self._download_subtitles_for_type(
                video_id, language, manual=False
            )
            if success:
                downloaded_files.extend(files)
        
        # Try English as fallback if original language failed
        elif language != "en" and "en" in subtitles["manual"]:
            logging.info(f"Requested language not available, trying English manual subtitles")
            success, files = self._download_subtitles_for_type(
                video_id, "en", manual=True
            )
            if success:
                downloaded_files.extend(files)
        
        elif language != "en" and "en" in subtitles["auto"]:
            logging.info(f"Requested language not available, trying English auto-generated subtitles")
            success, files = self._download_subtitles_for_type(
                video_id, "en", manual=False
            )
            if success:
                downloaded_files.extend(files)
        
        else:
            logging.warning(f"No subtitles available in {language} or English")
            return False, []
        
        return len(downloaded_files) > 0, downloaded_files
    
    def _download_subtitles_for_type(self, video_id: str, language: str, manual: bool = True) -> Tuple[bool, List[str]]:
        """
        Download subtitles of a specific type (manual or auto).
        
        Args:
            video_id: YouTube video ID
            language: Language code
            manual: Whether to download manual (True) or auto-generated (False) subtitles
            
        Returns:
            Tuple of (success, list of downloaded files)
        """
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Create output directory for this video
        video_dir = self.output_dir / video_id
        video_dir.mkdir(exist_ok=True)
        
        cmd = [
            "yt-dlp",
            "--write-subs" if manual else "--write-auto-subs",
            "--sub-langs", language,
            "--sub-format", "srt/best",
            "--skip-download",
            "--output", str(video_dir / "%(title)s.%(ext)s"),
            url
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                encoding='utf-8'
            )
            
            # Find downloaded subtitle files
            downloaded_files = []
            for file in video_dir.glob("*.srt"):
                downloaded_files.append(str(file))
                logging.info(f"Downloaded: {file.name}")
            
            for file in video_dir.glob("*.vtt"):
                downloaded_files.append(str(file))
                logging.info(f"Downloaded: {file.name}")
            
            return len(downloaded_files) > 0, downloaded_files
            
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to download subtitles: {e}")
            logging.error(f"stderr: {e.stderr}")
            return False, []
    
    def download_metadata(self, video_id: str) -> bool:
        """
        Download comprehensive video metadata as JSON.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            True if successful, False otherwise
        """
        video_info = self.get_video_info(video_id)
        if not video_info:
            return False
        
        # Create output directory for this video
        video_dir = self.output_dir / video_id
        video_dir.mkdir(exist_ok=True)
        
        # Save metadata as JSON
        metadata_file = video_dir / f"{video_id}_metadata.json"
        try:
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(video_info, f, indent=2, ensure_ascii=False)
            
            logging.info(f"Metadata saved to: {metadata_file}")
            return True
            
        except IOError as e:
            logging.error(f"Failed to save metadata: {e}")
            return False
    
    def extract_clean_subtitle_text(self, subtitle_file: str) -> Optional[str]:
        """
        Extract clean text from subtitle file (remove timestamps and formatting).
        
        Args:
            subtitle_file: Path to subtitle file
            
        Returns:
            Clean text content or None if failed
        """
        try:
            with open(subtitle_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple cleaning for SRT files
            lines = content.split('\n')
            clean_lines = []
            
            for line in lines:
                line = line.strip()
                # Skip empty lines, timestamps, and sequence numbers
                if (line and 
                    not line.isdigit() and 
                    not '-->' in line and 
                    not line.startswith('[') and 
                    not line.startswith('(')):
                    clean_lines.append(line)
            
            clean_text = ' '.join(clean_lines)
            clean_text = ' '.join(clean_text.split())  # Normalize whitespace
            
            # Save clean text
            clean_file = subtitle_file.replace('.srt', '_clean.txt').replace('.vtt', '_clean.txt')
            with open(clean_file, 'w', encoding='utf-8') as f:
                f.write(clean_text)
            
            logging.info(f"Clean text saved to: {clean_file}")
            return clean_text
            
        except Exception as e:
            logging.error(f"Failed to extract clean text: {e}")
            return None
    
    def process_video(self, video_id: str) -> bool:
        """
        Complete processing for a video: download subtitles, metadata, and extract clean text.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            True if successful, False otherwise
        """
        logging.info(f"Starting processing for video: {video_id}")
        
        # Download metadata
        metadata_success = self.download_metadata(video_id)
        if not metadata_success:
            logging.error("Failed to download metadata")
            return False
        
        # Download subtitles
        subtitle_success, subtitle_files = self.download_subtitles(video_id)
        if not subtitle_success:
            logging.error("Failed to download subtitles")
            return False
        
        # Extract clean text from each subtitle file
        for subtitle_file in subtitle_files:
            self.extract_clean_subtitle_text(subtitle_file)
        
        # Create summary report
        self.create_summary_report(video_id, subtitle_files)
        
        logging.info(f"Processing completed for video: {video_id}")
        return True
    
    def create_summary_report(self, video_id: str, subtitle_files: List[str]):
        """Create a summary report of downloaded content."""
        video_dir = self.output_dir / video_id
        
        # Load metadata
        metadata_file = video_dir / f"{video_id}_metadata.json"
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # Create summary
        summary = {
            "video_id": video_id,
            "title": metadata.get("title", "Unknown"),
            "uploader": metadata.get("uploader", "Unknown"),
            "duration": metadata.get("duration", 0),
            "upload_date": metadata.get("upload_date", "Unknown"),
            "view_count": metadata.get("view_count", 0),
            "original_language": metadata.get("language", "Unknown"),
            "downloaded_subtitles": subtitle_files,
            "clean_text_files": [f.replace('.srt', '_clean.txt').replace('.vtt', '_clean.txt') 
                               for f in subtitle_files]
        }
        
        # Save summary
        summary_file = video_dir / f"{video_id}_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Summary report saved to: {summary_file}")

def main():
    """Main function to handle command line usage."""
    if len(sys.argv) > 1:
        video_id = sys.argv[1]
    else:
        video_id = "IE1E9m5u488"
    
    downloader = YouTubeSubtitleDownloader()
    
    # Check if yt-dlp is installed
    if not downloader.check_yt_dlp_installed():
        sys.exit(1)
    
    # Process the video
    success = downloader.process_video(video_id)
    
    if success:
        print(f"\n✅ Successfully processed video: {video_id}")
        print(f"📁 Files saved in: downloads/{video_id}/")
    else:
        print(f"\n❌ Failed to process video: {video_id}")
        sys.exit(1)

if __name__ == "__main__":
    main()