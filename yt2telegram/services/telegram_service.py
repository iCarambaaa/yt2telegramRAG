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

    @network_retry
    def send_message(self, message: str, parse_mode: str = "HTML", disable_preview: bool = True):
        """Send message to all configured bots with network retry"""
        if not self.bots:
            logger.error("No bots configured")
            return False
        
        success = True
        for bot in self.bots:
            try:
                url = f"https://api.telegram.org/bot{bot['token']}/sendMessage"
                
                payload = {
                    'chat_id': bot['chat_id'],
                    'text': message,
                    'parse_mode': parse_mode,
                    'disable_web_page_preview': disable_preview
                }
                
                response = requests.post(url, json=payload, timeout=30)
                response.raise_for_status()
                
                logger.info("Message sent successfully", bot_name=bot['name'])
                
            except requests.exceptions.RequestException as e:
                logger.error("Failed to send message", bot_name=bot['name'], error=str(e))
                success = False
            except Exception as e:
                logger.error("Unexpected error sending message", bot_name=bot['name'], error=str(e))
                success = False
        
        return success

    def send_video_notification(self, channel_name: str, video_title: str, video_id: str, summary: str, channel_type: str = "default", published_date: str = None):
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
                    # Format title with published date if available
                    if published_date:
                        # Format date nicely (assuming YYYY-MM-DD format)
                        try:
                            from datetime import datetime
                            date_obj = datetime.strptime(published_date, "%Y-%m-%d")
                            formatted_date = date_obj.strftime("%B %d, %Y")
                            html_message += f"📺 <b>{escaped_title}</b>\n"
                            html_message += f"📅 <i>{formatted_date}</i>\n\n"
                        except:
                            # Fallback if date parsing fails
                            html_message += f"📺 <b>{escaped_title}</b>\n"
                            html_message += f"📅 <i>{published_date}</i>\n\n"
                    else:
                        html_message += f"📺 <b>{escaped_title}</b>\n\n"
                    html_message += f"━━━━━━━━━━━━━━━━━━━━\n\n"
                html_message += f"{clean_summary}"
                if part_index == total_parts - 1:
                    html_message += f"\n\n━━━━━━━━━━━━━━━━━━━━"
                    html_message += f"\n🔗 <a href=\"{video_url}\">Watch Full Video</a>"
                    if escaped_footer:
                        html_message += f"\n\n{escaped_footer}"
                
                # Enable thumbnail preview for the last part (which contains the video link)
                enable_preview = (part_index == total_parts - 1)
                self.send_message(html_message, parse_mode="HTML", disable_preview=not enable_preview)
                logger.info("Sent HTML formatted message part", part=part_index + 1, total_parts=total_parts, channel_name=channel_name)
                part_success = True
                
            except Exception as e:
                logger.warning("HTML formatting failed, trying fallback", error=str(e))
                
                # Fallback: Plain text with minimal formatting
                try:
                    # Strip all formatting and send as plain text
                    plain_summary = Sanitizer.strip_all_formatting(summary_part)
                    
                    plain_message = f"🎬 {part_header}\n\n"
                    if part_index == 0:
                        if published_date:
                            try:
                                from datetime import datetime
                                date_obj = datetime.strptime(published_date, "%Y-%m-%d")
                                formatted_date = date_obj.strftime("%B %d, %Y")
                                plain_message += f"📺 {video_title}\n"
                                plain_message += f"📅 {formatted_date}\n\n"
                            except:
                                plain_message += f"📺 {video_title}\n"
                                plain_message += f"📅 {published_date}\n\n"
                        else:
                            plain_message += f"📺 {video_title}\n\n"
                        plain_message += f"━━━━━━━━━━━━━━━━━━━━\n\n"
                    plain_message += f"{plain_summary}"
                    if part_index == total_parts - 1:
                        plain_message += f"\n\n━━━━━━━━━━━━━━━━━━━━"
                        plain_message += f"\n🔗 {video_url}"
                        if footer:
                            plain_message += f"\n\n{footer}"
                    
                    # Enable thumbnail preview for the last part (which contains the video link)
                    enable_preview = (part_index == total_parts - 1)
                    self.send_message(plain_message, parse_mode=None, disable_preview=not enable_preview)
                    logger.info("Sent plain text message part", part=part_index + 1, total_parts=total_parts, channel_name=channel_name)
                    part_success = True
                    
                except Exception as e2:
                    logger.error("Both HTML and plain text formatting failed", error=str(e2))
                    part_success = False
            
            if part_success:
                success = True
            
            # Small delay between parts to avoid rate limiting
            if part_index < total_parts - 1:
                time.sleep(1)
        
        if success:
            logger.info("Successfully sent notification", channel_name=channel_name)
        else:
            logger.error("Failed to send any message parts", channel_name=channel_name)
        
        return success