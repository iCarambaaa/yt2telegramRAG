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
        """Send message to a specific bot"""
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
                response.raise_for_status()
                
                logger.info(f"Message sent successfully to {bot['name']}")
                return
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed for {bot['name']}: {e}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay_seconds)
                else:
                    logger.error(f"Failed to send message to {bot['name']} after {self.retry_attempts} attempts")

    def send_video_notification(self, channel_name: str, video_title: str, video_id: str, summary: str, channel_type: str = "default"):
        """Send formatted video notification with proper formatting per channel"""
        
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        if channel_type == "isaac_arthur":
            # Special formatting for Isaac Arthur channel
            message = f"🚀 **New Isaac Arthur Video**\n\n"
            message += f"**{video_title}**\n\n"
            message += f"📝 **Summary:**\n{summary}\n\n"
            message += f"🔗 [Watch Video]({video_url})\n\n"
            message += f"#IsaacArthur #SciFi #FutureTech"
            
        elif channel_type == "robynhd":
            # Special formatting for RobynHD channel  
            message = f"💰 **Neues RobynHD Video**\n\n"
            message += f"**{video_title}**\n\n"
            message += f"📊 **Zusammenfassung:**\n{summary}\n\n"
            message += f"🎥 [Video ansehen]({video_url})\n\n"
            message += f"#RobynHD #Krypto #Trading"
            
        else:
            # Default formatting
            message = f"📺 **New Video from {channel_name}**\n\n"
            message += f"**{video_title}**\n\n"
            message += f"📝 **Summary:**\n{summary}\n\n"
            message += f"🔗 [Watch Video]({video_url})"
        
        # Try with Markdown first
        try:
            self.send_message(message, parse_mode="Markdown")
            logger.info(f"Sent formatted message for {channel_name}")
        except Exception as e:
            logger.warning(f"Failed to send with Markdown, trying MarkdownV2: {e}")
            try:
                escaped_message = Sanitizer.escape_markdown(message)
                self.send_message(escaped_message, parse_mode="MarkdownV2")
            except Exception as e2:
                logger.warning(f"Failed to send with MarkdownV2, trying plain text: {e2}")
                # Plain text fallback
                plain_message = f"New video from {channel_name}: {video_title}\n\nSummary: {summary}\nLink: {video_url}"
                self.send_message(plain_message, parse_mode=None)