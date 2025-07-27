import os
import logging
from telegram import Bot
from telegram.error import TelegramError
import asyncio

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self, bot_configs, retry_attempts: int = 3, retry_delay_seconds: int = 5):
        self.bots = []
        self.retry_attempts = retry_attempts
        self.retry_delay_seconds = retry_delay_seconds

        for config in bot_configs:
            token_env_var = config.get('token_env')
            chat_id = config.get('chat_id')
            bot_name = config.get('name', 'Unnamed Bot')

            if not token_env_var or not chat_id:
                logger.warning(f"Skipping {bot_name}: Missing token_env or chat_id in config.")
                continue

            token = os.getenv(token_env_var)
            if not token:
                logger.error(f"Telegram bot token for {bot_name} (env: {token_env_var}) not found in environment variables.")
                continue

            try:
                bot = Bot(token=token)
                self.bots.append({'name': bot_name, 'bot': bot, 'chat_id': chat_id})
                logger.info(f"Initialized Telegram bot: {bot_name}")
            except Exception as e:
                logger.error(f"Error initializing Telegram bot {bot_name}: {e}")

    async def send_message(self, text: str, parse_mode: str = "MarkdownV2"):
        if not self.bots:
            logger.warning("No Telegram bots initialized. Message will not be sent.")
            return

        for bot_info in self.bots:
            bot = bot_info['bot']
            chat_id = bot_info['chat_id']
            bot_name = bot_info['name']
            for attempt in range(self.retry_attempts):
                try:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=text,
                        parse_mode=parse_mode,
                        disable_web_page_preview=False,
                    )
                    logger.info(f"Message sent successfully via {bot_name} to chat {chat_id}")
                    break # Break out of retry loop on success
                except TelegramError as e:
                    logger.warning(f"Attempt {attempt + 1}/{self.retry_attempts} failed to send message via {bot_name} to chat {chat_id}: {e}")
                    if attempt < self.retry_attempts - 1:
                        await asyncio.sleep(self.retry_delay_seconds)
                except Exception as e:
                    logger.error(f"Unexpected error sending message via {bot_name} to chat {chat_id}: {e}")
                    break # Don't retry on unexpected errors
            else:
                logger.error(f"Failed to send message via {bot_name} to chat {chat_id} after {self.retry_attempts} attempts.")