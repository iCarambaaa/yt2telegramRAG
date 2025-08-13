import os
import logging
from typing import List, Dict
import time
import requests

from ..utils.validators import Sanitizer

logger = logging.getLogger(__name__)

class TelegramService:
    def __init__(self, bot_configs: List[Dict], retry_attempts: int = 3, retry_delay_seconds: int = 5):
        self.bots = []
        self.retry_attempts = retry_attempts
        self.retry_delay_seconds = retry_delay_seconds
        
        for config in bot_configs:
            bot_name = config.get('name', 'Unnamed Bot')
            
            # Get token from environment
            token_env_var = config.get('token_env')
            if not token_env_var:
                logger.warning(f"Skipping {bot_name}: Missing 'token_env' in config")
                continue
                
            token = os.getenv(token_env_var)
            if not token:
                logger.error(f"Token for {bot_name} not found in environment: {token_env_var}")
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
                logger.error(f"Chat ID for {bot_name} not found")
                continue
            
            self.bots.append({
                'name': bot_name,
                'token': token,
                'chat_id': chat_id
            })
        
        logger.info(f"Initialized {len(self.bots)} Telegram bots")

    def send_message(self, message: str, parse_mode: str = None):
        """Send message to all configured bots"""
        if not self.bots:
            logger.warning("No Telegram bots configured")
            return
        
        for bot in self.bots:
            self._send_to_bot(bot, message, parse_mode)

    def _send_to_bot(self, bot: Dict, message: str, parse_mode: str = None):
        """Send message to a specific bot with detailed error logging"""
        url = f"https://api.telegram.org/bot{bot['token']}/sendMessage"
        
        payload = {
            'chat_id': bot['chat_id'],
            'text': message
        }
        
        if parse_mode:
            payload['parse_mode'] = parse_mode
        
        for attempt in range(self.retry_attempts):
            try:
                response = requests.post(url, json=payload, timeout=30)
                
                if response.status_code == 200:
                    logger.info(f"Message sent successfully to {bot['name']}")
                    return
                else:
                    # Log detailed error information
                    error_details = ""
                    try:
                        error_json = response.json()
                        error_details = f"Error: {error_json.get('description', 'Unknown error')}"
                    except:
                        error_details = f"HTTP {response.status_code}: {response.text[:200]}"
                    
                    logger.warning(f"Attempt {attempt + 1} failed for {bot['name']}: {error_details}")
                    
                    # Don't retry on certain errors
                    if response.status_code == 400:  # Bad Request - likely formatting issue
                        raise requests.exceptions.RequestException(f"Bad Request: {error_details}")
                    
                    response.raise_for_status()
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed for {bot['name']}: {e}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay_seconds)
                else:
                    logger.error(f"Failed to send message to {bot['name']} after {self.retry_attempts} attempts")
                    raise  # Re-raise the exception so the caller can handle it

    def send_video_notification(self, channel_name: str, video_title: str, video_id: str, summary: str, channel_type: str = "default"):
        """Send formatted video notification with robust error handling"""
        
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Clean the summary for safe Telegram sending
        clean_summary = Sanitizer.clean_for_telegram(summary)
        summary_parts = Sanitizer.split_for_telegram(clean_summary, 3800)  # Leave room for headers
        
        # Create channel-specific headers
        if channel_type == "isaac_arthur":
            header = "🚀 New Isaac Arthur Video"
            footer = "#IsaacArthur #SciFi #FutureTech"
        elif channel_type == "robynhd":
            header = "💰 Neues RobynHD Video"
            footer = "#RobynHD #Krypto #Trading"
        else:
            header = f"📺 New Video from {channel_name}"
            footer = ""
        
        # Send messages (potentially multiple parts)
        success = False
        total_parts = len(summary_parts)
        
        for part_index, summary_part in enumerate(summary_parts):
            part_success = False
            
            # Create part-specific header
            if total_parts > 1:
                part_header = f"{header} - Part {part_index + 1}/{total_parts}"
            else:
                part_header = header
            
            # Approach 1: Simple HTML formatting (most reliable)
            try:
                # Escape HTML in content to prevent parsing errors
                escaped_title = Sanitizer.escape_html(video_title)
                escaped_summary = Sanitizer.escape_html(summary_part)
                escaped_footer = Sanitizer.escape_html(footer) if footer else ""
                
                html_message = f"<b>{part_header}</b>\n\n"
                if part_index == 0:  # Only add title to first part
                    html_message += f"<b>{escaped_title}</b>\n\n"
                html_message += f"📝 <b>Summary:</b>\n{escaped_summary}\n\n"
                if part_index == total_parts - 1:  # Only add link to last part
                    html_message += f"🔗 <a href='{video_url}'>Watch Video</a>"
                    if escaped_footer:
                        html_message += f"\n\n{escaped_footer}"
                
                self.send_message(html_message, parse_mode="HTML")
                logger.info(f"Sent HTML formatted message part {part_index + 1}/{total_parts} for {channel_name}")
                part_success = True
                
            except Exception as e:
                logger.warning(f"HTML formatting failed for {channel_name} part {part_index + 1}: {e}")
            
            # Approach 2: Basic Markdown (if HTML fails)
            if not part_success:
                try:
                    md_message = f"*{part_header}*\n\n"
                    if part_index == 0:
                        md_message += f"*{video_title}*\n\n"
                    md_message += f"📝 *Summary:*\n{summary_part}\n\n"
                    if part_index == total_parts - 1:
                        md_message += f"🔗 {video_url}"
                        if footer:
                            md_message += f"\n\n{footer}"
                    
                    self.send_message(md_message, parse_mode="Markdown")
                    logger.info(f"Sent Markdown formatted message part {part_index + 1}/{total_parts} for {channel_name}")
                    part_success = True
                    
                except Exception as e:
                    logger.warning(f"Markdown formatting failed for {channel_name} part {part_index + 1}: {e}")
            
            # Approach 3: Plain text (guaranteed to work)
            if not part_success:
                try:
                    plain_message = f"{part_header}\n\n"
                    if part_index == 0:
                        plain_message += f"{video_title}\n\n"
                    plain_message += f"📝 Summary:\n{summary_part}\n\n"
                    if part_index == total_parts - 1:
                        plain_message += f"🔗 Watch: {video_url}"
                        if footer:
                            plain_message += f"\n\n{footer}"
                    
                    self.send_message(plain_message, parse_mode=None)
                    logger.info(f"Sent plain text message part {part_index + 1}/{total_parts} for {channel_name}")
                    part_success = True
                    
                except Exception as e:
                    logger.error(f"Even plain text failed for {channel_name} part {part_index + 1}: {e}")
            
            if part_success:
                success = True
            else:
                logger.error(f"Failed to send part {part_index + 1}/{total_parts} for {channel_name}")
                break  # Stop sending remaining parts if one fails
            
            # Small delay between parts to avoid rate limiting
            if part_index < total_parts - 1:
                time.sleep(1)
        
        if success:
            logger.info(f"Successfully sent notification for {channel_name}")
        else:
            logger.error(f"All formatting attempts failed for {channel_name}")