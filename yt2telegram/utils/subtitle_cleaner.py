import re
from pathlib import Path
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class SubtitleCleaner:
    def __init__(self):
        pass
    
    def clean_vtt_subtitles(self, vtt_content: str) -> str:
        """Clean VTT subtitle content to readable text"""
        lines = vtt_content.split('\n')
        
        # Skip WEBVTT header and metadata
        start_index = 0
        for i, line in enumerate(lines):
            if line.strip() == "WEBVTT":
                start_index = i + 1
                break

        cleaned_lines = []
        current_text = []

        for line in lines[start_index:]:
            line = line.strip()
            
            # Skip empty lines, timestamps, and sequence numbers
            if not line or '-->' in line or line.isdigit():
                if current_text:
                    text = ' '.join(current_text).strip()
                    if text:
                        cleaned_lines.append(text)
                    current_text = []
                continue

            # Skip metadata lines
            if (line.startswith('NOTE') or line.startswith('STYLE') or 
                line.startswith('Kind:') or line.startswith('Language:')):
                continue

            # Clean the line
            if line:
                # Remove HTML tags
                line = re.sub(r'<[^>]+>', '', line)
                
                # Remove music symbols and sound effects
                line = re.sub(r'[♪♫♬♩🎵🎶]', '', line)
                line = re.sub(r'\[.*?\]', '', line)  # Remove [sound effects]
                line = re.sub(r'\(.*?\)', '', line)  # Remove (background noise)
                
                # Clean up whitespace
                line = re.sub(r'\s+', ' ', line).strip()
                
                if line:
                    current_text.append(line)

        # Add any remaining text
        if current_text:
            text = ' '.join(current_text).strip()
            if text:
                cleaned_lines.append(text)

        # Join all text and final cleanup
        result = ' '.join(cleaned_lines)
        result = re.sub(r'\s+', ' ', result)  # Normalize whitespace
        result = re.sub(r'(\w)([.!?])(\w)', r'\1\2 \3', result)  # Fix punctuation spacing
        result = result.strip()

        return result

    def process_subtitle_file(self, file_path: str) -> str:
        """Process subtitle file with basic VTT cleaning only"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_subtitles = f.read()
            
            # Basic VTT cleaning is sufficient
            cleaned_text = self.clean_vtt_subtitles(raw_subtitles)
            logger.info(f"Cleaned subtitles: {len(raw_subtitles)} -> {len(cleaned_text)} characters")
            return cleaned_text
            
        except Exception as e:
            logger.error(f"Error processing subtitle file {file_path}: {e}")
            return ""