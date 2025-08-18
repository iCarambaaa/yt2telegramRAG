import re
from typing import Any, List

class ValidationError(Exception):
    pass

class InputValidator:
    @staticmethod
    def validate_telegram_chat_id(chat_id: Any) -> int:
        """Validate and convert telegram chat ID to integer"""
        try:
            chat_id_int = int(chat_id)
            return chat_id_int
        except (ValueError, TypeError):
            raise ValidationError(f"Invalid chat ID format: {chat_id}")
    
    @staticmethod
    def validate_youtube_channel_id(channel_id: str) -> str:
        """Validate YouTube channel ID format"""
        if not channel_id or not isinstance(channel_id, str):
            raise ValidationError("Channel ID must be a non-empty string")
        
        # YouTube channel IDs are typically 24 characters starting with UC
        if not re.match(r'^UC[a-zA-Z0-9_-]{22}$', channel_id):
            raise ValidationError(f"Invalid YouTube channel ID format: {channel_id}")
        
        return channel_id

class Sanitizer:

    
    @staticmethod
    def escape_html(text: str) -> str:
        """Escape HTML special characters according to Telegram Bot API"""
        if not text:
            return text
        
        # Telegram HTML formatting requires escaping these characters
        # According to: https://core.telegram.org/bots/api#html-style
        html_escapes = {
            '&': '&amp;',   # Must be first to avoid double-escaping
            '<': '&lt;',
            '>': '&gt;',
        }
        
        for char, escape in html_escapes.items():
            text = text.replace(char, escape)
        
        return text
    
    @staticmethod
    def escape_markdown_v2(text: str) -> str:
        """Escape special characters for Telegram MarkdownV2 according to Bot API"""
        if not text:
            return text
        
        # According to Telegram Bot API, these characters must be escaped in MarkdownV2:
        # _*[]()~`>#+-=|{}.!
        # But we need to be careful not to escape characters that are part of formatting
        escape_chars = r'_*[]()~`>#+-=|{}.!'
        escaped_text = ""
        
        for char in text:
            if char in escape_chars:
                escaped_text += f"\\{char}"
            else:
                escaped_text += char
        
        return escaped_text
    

    
    @staticmethod
    def clean_for_telegram(text: str) -> str:
        """Clean markdown text for Telegram messages"""
        if not text:
            return text
        
        # Clean problematic patterns while preserving markdown
        text = re.sub(r'[~{}+=\[\]]', '', text)  # Remove special chars
        text = re.sub(r'[|]', ' ', text)  # Remove table separators
        text = re.sub(r'[-]{3,}', '\n━━━━━━━━━━\n', text)  # Convert horizontal rules to visual separator
        text = re.sub(r'>\s*', '', text, flags=re.MULTILINE)  # Remove blockquotes
        
        # Fix spacing issues
        text = re.sub(r'[ \t]+', ' ', text)  # Normalize spaces/tabs but keep newlines
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Max 2 consecutive newlines
        
        # Fix punctuation
        text = re.sub(r'\.{3,}', '...', text)  # Normalize ellipsis
        text = re.sub(r'!{2,}', '!', text)  # Single exclamation
        text = re.sub(r'\?{2,}', '?', text)  # Single question mark
        text = re.sub(r'--+', ' — ', text)  # Replace dashes with em-dash
        
        # Final cleanup
        text = re.sub(r'\n{3,}', '\n\n', text)  # Max 2 consecutive newlines
        text = text.strip()
        
        return text
    

    @staticmethod
    def convert_markdown_to_clean_html(text: str) -> str:
        """Convert simple markdown formatting to clean Telegram HTML"""
        if not text:
            return text
        
        # Convert **bold** to <b>bold</b>
        text = re.sub(r'\*\*([^*\n]+?)\*\*', r'<b>\1</b>', text)
        
        # Convert `code` to <code>code</code>
        text = re.sub(r'`([^`\n]+?)`', r'<code>\1</code>', text)
        
        # Escape any remaining HTML characters in the text
        # But preserve our newly created <b> and <code> tags
        parts = re.split(r'(</?(?:b|code)>)', text)
        escaped_parts = []
        
        for part in parts:
            if part in ['<b>', '</b>', '<code>', '</code>']:
                escaped_parts.append(part)
            else:
                # Escape HTML in regular text but preserve line breaks and structure
                escaped_part = part.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                escaped_parts.append(escaped_part)
        
        return ''.join(escaped_parts)
    
    @staticmethod
    def validate_telegram_message(text: str) -> bool:
        """Validate message meets Telegram Bot API requirements"""
        if not text:
            return False
        
        # Telegram message limits according to Bot API
        MAX_MESSAGE_LENGTH = 4096
        
        if len(text) > MAX_MESSAGE_LENGTH:
            return False
        
        return True
    
    @staticmethod
    def split_for_telegram(text: str, max_length: int = 3800) -> List[str]:
        """Split text into multiple messages that fit Telegram's limits while preserving all content"""
        if len(text) <= max_length:
            return [text]
        
        messages = []
        remaining_text = text
        part_number = 1
        
        while remaining_text:
            if len(remaining_text) <= max_length:
                # Last part
                if len(messages) > 0:  # Only add part number if there are multiple parts
                    messages.append(f"📄 Part {part_number}/{part_number}\n\n{remaining_text}")
                else:
                    messages.append(remaining_text)
                break
            
            # Find the best split point
            chunk = remaining_text[:max_length]
            
            # Look for good split points in order of preference
            split_points = [
                (chunk.rfind('\n\n'), 'paragraph'),  # Paragraph break
                (chunk.rfind('. '), 'sentence'),     # Sentence end
                (chunk.rfind('! '), 'sentence'),     # Exclamation
                (chunk.rfind('? '), 'sentence'),     # Question
                (chunk.rfind('\n'), 'line'),         # Line break
                (chunk.rfind(' '), 'word')           # Word boundary
            ]
            
            split_pos = max_length
            for pos, split_type in split_points:
                if pos > max_length * 0.6:  # Keep at least 60% of chunk
                    split_pos = pos + (1 if split_type == 'sentence' else 0)
                    break
            
            # Calculate total parts estimate (will be corrected later)
            total_parts = max(2, (len(text) // max_length) + 1)
            
            # Add this part
            part_text = remaining_text[:split_pos].strip()
            messages.append(f"📄 Part {part_number}/{total_parts}\n\n{part_text}")
            
            # Move to next part
            remaining_text = remaining_text[split_pos:].strip()
            part_number += 1
        
        # Fix part numbers now that we know the actual total
        actual_total = len(messages)
        if actual_total > 1:
            for i in range(len(messages)):
                # Replace the estimated total with the actual total
                old_pattern = re.search(r'📄 Part (\d+)/(\d+)', messages[i])
                if old_pattern:
                    messages[i] = re.sub(r'📄 Part (\d+)/(\d+)', f'📄 Part {i+1}/{actual_total}', messages[i], 1)
        
        return messages
    
    @staticmethod
    def truncate_for_telegram(text: str, max_length: int = 3800) -> str:
        """Legacy truncate method - use split_for_telegram instead to preserve all content"""
        parts = Sanitizer.split_for_telegram(text, max_length)
        return parts[0]  # Return only first part for backward compatibility