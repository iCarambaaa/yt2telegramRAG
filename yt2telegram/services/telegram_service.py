import os
import time
from typing import List, Dict
import requests
import re

from ..utils.validators import Sanitizer
from ..utils.retry import network_retry, retry
from ..utils.logging_config import LoggerFactory

logger = LoggerFactory.create_logger(__name__)

class TelegramService:
    def __init__(self, bot_configs: List[Dict]):
        self.bots = []
        
        for config in bot_configs:
            bot_name = config.get('name', 'Unnamed Bot')
            
            # Get token from environment
            token_env_var = config.get('token_env')
            if not token_env_var:
                logger.warning("Skipping bot: Missing 'token_env' in config", bot_name=bot_name)
                continue
                
            token = os.getenv(token_env_var)
            if not token:
                logger.error("Token not found in environment", bot_name=bot_name, token_env_var=token_env_var)
                continue
            
            # Get chat ID
            chat_id_env = config.get('chat_id_env')
            chat_id_direct = config.get('chat_id')
            
            chat_id = None
            if chat_id_env:
                chat_id = os.getenv(chat_id_env)
            if not chat_id and chat_id_direct:
                chat_id = str(chat_id_direct)
            
            if not chat_id:
                logger.error("Chat ID not found", bot_name=bot_name)
                continue
            
            self.bots.append({
                'name': bot_name,
                'token': token,
                'chat_id': chat_id
            })
        
        logger.info("Initialized Telegram bots", count=len(self.bots))

    def send_message(self, message: str, parse_mode: str = None):
        """Send message to all configured bots"""
        if not self.bots:
            logger.warning("No Telegram bots configured")
            return
        
        for bot in self.bots:
            self._send_to_bot(bot, message, parse_mode)

    @network_retry
    def _send_to_bot(self, bot: Dict, message: str, parse_mode: str = None):
        """Send message to a specific bot with detailed error logging"""
        url = f"https://api.telegram.org/bot{bot['token']}/sendMessage"
        
        payload = {
            'chat_id': bot['chat_id'],
            'text': message
        }
        
        if parse_mode:
            payload['parse_mode'] = parse_mode
        
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 200:
            logger.info("Message sent successfully", bot_name=bot['name'])
            return
        else:
            # Log detailed error information
            error_details = ""
            try:
                error_json = response.json()
                error_details = f"Error: {error_json.get('description', 'Unknown error')}"
            except:
                error_details = f"HTTP {response.status_code}: {response.text[:200]}"
            
            # Don't retry on certain errors
            if response.status_code == 400:  # Bad Request - likely formatting issue
                raise requests.exceptions.RequestException(f"Bad Request: {error_details}")
            
            response.raise_for_status()


    
    def send_video_notification(self, channel_name: str, video_title: str, video_id: str, summary: str, channel_type: str = "default"):
        """Send formatted video notification with robust error handling"""
        
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Clean the summary for safe Telegram sending
        clean_summary = Sanitizer.clean_for_telegram(summary)
        summary_parts = Sanitizer.split_for_telegram(clean_summary, 3800)  # Leave room for headers
        
        # Create channel-specific headers (lol)
        if channel_type == "isaac_arthur":
            header = "🚀 New Isaac Arthur Video"
            footer = "#IsaacArthur #SciFi #FutureTech"
        elif channel_type == "robynhd":
            header = "💰 Neues RobynHD Video"
            footer = "#RobynHD #Krypto #Trading"
        else:
            header = f"📺 New Video from {channel_name}"
            footer = ""
        
        # Send messages (potentially multiple parts) - Direct MarkdownV2 from LLM
        success = False
        total_parts = len(summary_parts)
        
        for part_index, summary_part in enumerate(summary_parts):
            part_success = False
            
            # Create part-specific header
            if total_parts > 1:
                part_header = f"{header} - Part {part_index + 1}/{total_parts}"
            else:
                part_header = header
            
            # Primary Approach: Convert markdown-style to clean HTML
            try:
                # Convert the LLM's markdown-style output to clean HTML
                clean_summary = Sanitizer.convert_markdown_to_clean_html(summary_part)
                
                # Escape only the header and title
                escaped_header = Sanitizer.escape_html(part_header)
                escaped_title = Sanitizer.escape_html(video_title)
                escaped_footer = Sanitizer.escape_html(footer) if footer else ""
                
                html_message = f"🎬 <b>{escaped_header}</b>\n\n"
                if part_index == 0:
                    html_message += f"📺 <b>{escaped_title}</b>\n\n"
                    html_message += f"━━━━━━━━━━━━━━━━━━━━\n\n"
                html_message += f"{clean_summary}\n\n"
                if part_index == total_parts - 1:
                    html_message += f"━━━━━━━━━━━━━━━━━━━━\n"
                    html_message += f"🔗 <a href=\"{video_url}\">Watch Full Video</a>"
                    if escaped_footer:
                        html_message += f"\n\n{escaped_footer}"
                
                self.send_message(html_message, parse_mode="HTML")
                logger.info("Sent HTML formatted message part", part=part_index + 1, total_parts=total_parts, channel_name=channel_name)
                part_success = True
                
            except Exception as e:
                logger.warning("HTML formatting failed", channel_name=channel_name, part=part_index + 1, error=str(e))
            
            # Fallback: Plain text (guaranteed to work)
            if not part_success:
                try:
                    # Clean the summary for plain text by removing HTML formatting
                    plain_summary = summary_part
                    plain_summary = re.sub(r'<b>([^<]+)</b>', r'\1', plain_summary)    # Remove <b>bold</b>
                    plain_summary = re.sub(r'<i>([^<]+)</i>', r'\1', plain_summary)    # Remove <i>italic</i>
                    plain_summary = re.sub(r'<code>([^<]+)</code>', r'\1', plain_summary)  # Remove <code>code</code>
                    plain_summary = re.sub(r'<[^>]+>', '', plain_summary)          # Remove any remaining HTML tags
                    plain_summary = re.sub(r'&amp;', '&', plain_summary)           # Unescape HTML entities
                    plain_summary = re.sub(r'&lt;', '<', plain_summary)
                    plain_summary = re.sub(r'&gt;', '>', plain_summary)
                    
                    plain_message = f"🎬 {part_header}\n\n"
                    if part_index == 0:
                        plain_message += f"📺 {video_title}\n\n"
                        plain_message += f"━━━━━━━━━━━━━━━━━━━━\n\n"
                    plain_message += f"{plain_summary}\n\n"
                    if part_index == total_parts - 1:
                        plain_message += f"━━━━━━━━━━━━━━━━━━━━\n"
                        plain_message += f"🔗 Watch: {video_url}"
                        if footer:
                            plain_message += f"\n\n{footer}"
                    
                    self.send_message(plain_message, parse_mode=None)
                    logger.info("Sent plain text message part", part=part_index + 1, total_parts=total_parts, channel_name=channel_name)
                    part_success = True
                    
                except Exception as e:
                    logger.error("Even plain text failed", channel_name=channel_name, part=part_index + 1, error=str(e))
            
            if part_success:
                success = True
            else:
                logger.error("Failed to send part", part=part_index + 1, total_parts=total_parts, channel_name=channel_name)
                break  # Stop sending remaining parts if one fails
            
            # Small delay between parts to avoid rate limiting
            if part_index < total_parts - 1:
                time.sleep(1)
        
        if success:
            logger.info("Successfully sent notification", channel_name=channel_name)
        else:
            logger.error("All formatting attempts failed", channel_name=channel_name)