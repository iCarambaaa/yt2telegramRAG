import re
from pathlib import Path
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class SubtitleCleaner:
    def __init__(self):
        pass
    
    def clean_vtt_subtitles(self, vtt_content: str) -> str:
        """Clean VTT subtitle content to readable text with deduplication"""
        lines = vtt_content.split('\n')
        
        # Skip WEBVTT header and metadata
        start_index = 0
        for i, line in enumerate(lines):
            if line.strip() == "WEBVTT":
                start_index = i + 1
                break

        subtitle_blocks = []
        current_block = []
        
        # Parse subtitle blocks
        for line in lines[start_index:]:
            line = line.strip()
            
            # Skip metadata lines
            if (line.startswith('NOTE') or line.startswith('STYLE') or 
                line.startswith('Kind:') or line.startswith('Language:')):
                continue
            
            # Timestamp line indicates start of new block
            if '-->' in line:
                if current_block:
                    subtitle_blocks.append(current_block)
                current_block = []
                continue
            
            # Skip empty lines and sequence numbers
            if not line or line.isdigit():
                continue
                
            # Clean the line
            if line:
                # Remove HTML tags and timing info
                line = re.sub(r'<[^>]*>', '', line)
                
                # Remove music symbols and sound effects
                line = re.sub(r'[♪♫♬♩🎵🎶]', '', line)
                line = re.sub(r'\[.*?\]', '', line)  # Remove [sound effects]
                line = re.sub(r'\(.*?\)', '', line)  # Remove (background noise)
                
                # Clean up whitespace
                line = re.sub(r'\s+', ' ', line).strip()
                
                if line:
                    current_block.append(line)
        
        # Add final block
        if current_block:
            subtitle_blocks.append(current_block)
        
        # Deduplicate overlapping content
        final_text = self._deduplicate_subtitle_blocks(subtitle_blocks)
        
        # Final cleanup
        final_text = re.sub(r'\s+', ' ', final_text)  # Normalize whitespace
        final_text = re.sub(r'(\w)([.!?])(\w)', r'\1\2 \3', final_text)  # Fix punctuation spacing
        final_text = final_text.strip()

        return final_text
    
    def _deduplicate_subtitle_blocks(self, blocks: list) -> str:
        """Remove overlapping text from subtitle blocks"""
        if not blocks:
            return ""
        
        result_words = []
        
        for block in blocks:
            block_text = ' '.join(block)
            block_words = block_text.split()
            
            if not result_words:
                # First block, add all words
                result_words.extend(block_words)
            else:
                # Find overlap with previous content
                overlap_found = False
                
                # Check for overlap by looking for matching sequences
                for i in range(min(len(block_words), len(result_words))):
                    # Check if the last i+1 words of result match first i+1 words of block
                    if i + 1 <= len(result_words):
                        result_tail = result_words[-(i+1):]
                        block_head = block_words[:i+1]
                        
                        if result_tail == block_head:
                            # Found overlap, add only the non-overlapping part
                            new_words = block_words[i+1:]
                            result_words.extend(new_words)
                            overlap_found = True
                            break
                
                if not overlap_found:
                    # No overlap found, add all words
                    result_words.extend(block_words)
        
        return ' '.join(result_words)

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