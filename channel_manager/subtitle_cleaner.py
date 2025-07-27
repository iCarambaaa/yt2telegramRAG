

import re
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SubtitleCleaner:
    def clean_vtt_subtitles(self, vtt_content: str) -> str:
        lines = vtt_content.split('\n')
        start_index = 0
        for i, line in enumerate(lines):
            if line.strip() == "WEBVTT":
                start_index = i + 1
                break

        cleaned_lines = []
        current_text = []

        for line in lines[start_index:]:
            line = line.strip()
            if not line or '-->' in line or line.isdigit():
                if current_text:
                    text = ' '.join(current_text).strip()
                    if text:
                        cleaned_lines.append(text)
                    current_text = []
                continue

            if line and not line.startswith('NOTE') and not line.startswith('STYLE'):
                line = re.sub(r'<[^>]+>', '', line)
                line = re.sub(r'\s+', ' ', line).strip()
                if line:
                    current_text.append(line)

        if current_text:
            text = ' '.join(current_text).strip()
            if text:
                cleaned_lines.append(text)

        result = ' '.join(cleaned_lines)
        result = re.sub(r'\s+', ' ', result)
        result = re.sub(r'(\w)([.!?])(\w)', r'\1\2 \3', result)
        result = result.strip()

        return result

    def process_subtitle_file(self, file_path: str) -> str:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_subtitles = f.read()
            cleaned_text = self.clean_vtt_subtitles(raw_subtitles)
            return cleaned_text
        except Exception as e:
            logger.error(f"Error processing subtitle file {file_path}: {e}")
            return ""

