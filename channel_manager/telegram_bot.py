import os
import logging
from telegram import Bot, Update
from telegram.error import TelegramError
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import asyncio
from typing import Dict, List, Optional
import yaml
from pathlib import Path

from .exceptions import ConfigurationError, TelegramAPIError
from .validators import InputValidator, Sanitizer
from .qna.handler import QnAHandler
from .qna.database import DatabaseQuery

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self, bot_configs, retry_attempts: int = 3, retry_delay_seconds: int = 5):
        self.bots = []
        self.retry_attempts = retry_attempts
        self.retry_delay_seconds = retry_delay_seconds
        self.qna_handlers = {}  # Store Q&A handlers by bot name
        self.applications = {}   # Store telegram applications for polling

        for config in bot_configs:
            bot_name = config.get('name', 'Unnamed Bot')
            
            # Validate and get token
            token_env_var = config.get('token_env')
            if not token_env_var:
                logger.warning(f"Skipping {bot_name}: Missing 'token_env' in config.")
                continue
            token = os.getenv(token_env_var)
            if not token:
                logger.error(f"Telegram bot token for {bot_name} (env: {token_env_var}) not found in environment variables.")
                continue

            # Validate and get chat ID with layered priority
            chat_id_env = config.get('chat_id_env')
            chat_id_direct = config.get('chat_id')
            
            actual_chat_id = None
            if chat_id_env:
                env_chat_id = os.getenv(chat_id_env)
                if env_chat_id:
                    try:
                        actual_chat_id = InputValidator.validate_telegram_chat_id(env_chat_id)
                    except ValidationError as e:
                        logger.error(f"Invalid chat ID from environment variable {chat_id_env} for {bot_name}: {e}")
                else:
                    logger.error(f"Telegram chat ID for {bot_name} (env: {chat_id_env}) not found in environment variables.")
            
            if actual_chat_id is None and chat_id_direct is not None:
                try:
                    actual_chat_id = InputValidator.validate_telegram_chat_id(chat_id_direct)
                except ValidationError as e:
                    logger.error(f"Invalid direct chat ID for {bot_name}: {e}")
            
            if actual_chat_id is None:
                logger.warning(f"Skipping {bot_name}: No valid chat ID found (neither direct nor from environment variable).")
                continue

            try:
                bot = Bot(token=token)
                self.bots.append({'name': bot_name, 'bot': bot, 'chat_id': actual_chat_id})
                
                # Initialize Q&A handler if database path is provided
                db_path = config.get('db_path')
                openrouter_key = os.getenv('OPENROUTER_API_KEY')
                if db_path and openrouter_key:
                    self.qna_handlers[bot_name] = QnAHandler(db_path, openrouter_key)
                    logger.info(f"Initialized Q&A handler for bot: {bot_name}")
                
                logger.info(f"Initialized Telegram bot: {bot_name}")
            except Exception as e:
                logger.error(f"Error initializing Telegram bot {bot_name}: {e}")

    async def send_message(self, text: str, parse_mode: str = "MarkdownV2"):
        if not self.bots:
            logger.warning("No Telegram bots initialized. Message will not be sent.")
            return

        # Sanitize the text for Telegram MarkdownV2 before sending
        sanitized_text = Sanitizer.sanitize_telegram_message(text)

        for bot_info in self.bots:
            bot = bot_info['bot']
            chat_id = bot_info['chat_id']
            bot_name = bot_info['name']
            for attempt in range(self.retry_attempts):
                try:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=sanitized_text,
                        parse_mode=parse_mode,
                        disable_web_page_preview=False,
                    )
                    logger.info(f"Message sent successfully via {bot_name} to chat {chat_id}")
                    break
                except TelegramError as e:
                    logger.warning(f"Attempt {attempt + 1}/{self.retry_attempts} failed to send message via {bot_name} to chat {chat_id}: {e}")
                    if attempt < self.retry_attempts - 1:
                        await asyncio.sleep(self.retry_delay_seconds)
                except Exception as e:
                    logger.error(f"Unexpected error sending message via {bot_name} to chat {chat_id}: {e}")
                    break
            else:
                logger.error(f"Failed to send message via {bot_name} to chat {chat_id} after {self.retry_attempts} attempts.")

    async def start_qna_polling(self, channel_configs):
        """Start Q&A polling for all configured bots"""
        for config in channel_configs:
            bot_name = config.get('name', 'Unnamed Bot')
            token_env_var = config.get('token_env')
            if not token_env_var:
                continue
                
            token = os.getenv(token_env_var)
            if not token:
                continue

            # Check if this bot has Q&A enabled
            db_path = config.get('db_path')
            openrouter_key = os.getenv('OPENROUTER_API_KEY')
            if not db_path or not openrouter_key:
                continue

            try:
                # Create application for this bot
                application = Application.builder().token(token).build()
                
                # Store configuration for handlers
                application.bot_data['config'] = config
                application.bot_data['qna_handler'] = self.qna_handlers.get(bot_name)
                
                # Add handlers
                application.add_handler(CommandHandler("start", self._start_command))
                application.add_handler(CommandHandler("help", self._help_command))
                application.add_handler(CommandHandler("latest", self._latest_command))
                application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))
                
                # Start polling
                await application.initialize()
                await application.start()
                await application.updater.start_polling()
                
                self.applications[bot_name] = application
                logger.info(f"Started Q&A polling for bot: {bot_name}")
                
            except Exception as e:
                logger.error(f"Error starting Q&A polling for {bot_name}: {e}")

    async def stop_qna_polling(self):
        """Stop all Q&A polling applications"""
        for bot_name, application in self.applications.items():
            try:
                await application.stop()
                logger.info(f"Stopped Q&A polling for bot: {bot_name}")
            except Exception as e:
                logger.error(f"Error stopping Q&A polling for {bot_name}: {e}")

    async def _start_command(self, update: Update, context):
        """Handle /start command"""
        welcome_message = (
            "🤖 **YouTube Q&A Bot**\n\n"
            "I can help you find information from YouTube videos!\n\n"
            "**Commands:**\n"
            "/start - Show this help message\n"
            "/help - Show detailed help\n"
            "/latest - Get latest video summaries\n\n"
            "**Usage:**\n"
            "• Ask me questions about video content\n"
            "• Search for specific topics\n"
            "• Get summaries of latest videos\n\n"
            "Just send me your question!"
        )
        await update.message.reply_text(welcome_message, parse_mode="Markdown")

    async def _help_command(self, update: Update, context):
        """Handle /help command"""
        help_message = (
            "📚 **Help - YouTube Q&A Bot**\n\n"
            "**Available Commands:**\n"
            "/start - Welcome message and basic usage\n"
            "/help - This detailed help message\n"
            "/latest - Get summaries of the 3 most recent videos\n\n"
            "**How to use:**\n"
            "1. **Ask Questions**: Simply type your question about any video content\n"
            "2. **Search Topics**: Ask about specific topics, people, or concepts\n"
            "3. **Get Context**: I'll search through video summaries and subtitles\n"
            "4. **Latest Videos**: Use /latest to see recent uploads\n\n"
            "**Examples:**\n"
            "• \"What did they say about climate change?\"\n"
            "• \"Tell me about the latest video on space exploration\"\n"
            "• \"Search for mentions of artificial intelligence\"\n"
            "• \"What was discussed in the last video?\"\n\n"
            "I'll search through all available video content to find relevant answers!"
        )
        await update.message.reply_text(help_message, parse_mode="Markdown")

    async def _latest_command(self, update: Update, context):
        """Handle /latest command"""
        bot_name = None
        for name, app in self.applications.items():
            if app.bot.id == context.bot.id:
                bot_name = name
                break
        
        if bot_name and bot_name in self.qna_handlers:
            qna_handler = self.qna_handlers[bot_name]
            response = qna_handler.get_latest_summary()
            await update.message.reply_text(response, parse_mode="Markdown")
        else:
            await update.message.reply_text("Sorry, I couldn't retrieve the latest videos.")

    async def _handle_message(self, update: Update, context):
        """Handle incoming text messages for Q&A"""
        bot_name = None
        for name, app in self.applications.items():
            if app.bot.id == context.bot.id:
                bot_name = name
                break
        
        if bot_name and bot_name in self.qna_handlers:
            qna_handler = self.qna_handlers[bot_name]
            question = update.message.text
            
            # Show typing indicator
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            
            # Process the question
            response = qna_handler.search_and_answer(question)
            await update.message.reply_text(response, parse_mode="Markdown")
        else:
            await update.message.reply_text("Sorry, I'm not configured for Q&A at the moment.")