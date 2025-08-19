"""Main Q&A Telegram bot with message receiving."""
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from .config import QnAConfig
from .handler import QnAHandler
from ..utils.logging_config import setup_logging, LoggerFactory

# Configure logging
setup_logging()
logger = LoggerFactory.create_logger(__name__)

class QnABot:
    """Q&A Telegram bot with message receiving."""
    
    def __init__(self, config_path: str):
        """Initialize bot with configuration."""
        self.config = QnAConfig(config_path)
        self.handler = None
        
        if not self.config.validate():
            raise ValueError("Invalid configuration. Please check bot token, chat ID, database path, and OpenRouter key.")
        
        self.application = Application.builder().token(self.config.bot_token).build()
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Set up command handlers."""
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("ask", self.ask))
        self.application.add_handler(CommandHandler("search", self.search))
        self.application.add_handler(CommandHandler("latest", self.latest))
        self.application.add_handler(CommandHandler("help", self.help))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        welcome_text = f"""
🤖 **{self.config.channel_name} Q&A Bot**

I'm here to help you ask questions about the channel's content!

**Available commands:**
• `/ask <question>` - Ask about any video content
• `/search <keywords>` - Search video summaries
• `/latest` - Get latest video summaries
• `/help` - Show this help message

Simply send me your question and I'll search through all video summaries and subtitles to provide an answer!
        """
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    async def ask(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ask command."""
        if not context.args:
            await update.message.reply_text(
                "Please provide a question after /ask\nExample: `/ask What is quantum computing?`",
                parse_mode='Markdown'
            )
            return
        
        question = ' '.join(context.args)
        await self._process_question(update, question)
    
    async def search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /search command."""
        if not context.args:
            await update.message.reply_text(
                "Please provide search keywords after /search\nExample: `/search space exploration`",
                parse_mode='Markdown'
            )
            return
        
        query = ' '.join(context.args)
        await self._process_search(update, query)
    
    async def latest(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /latest command."""
        try:
            if not self.handler:
                self.handler = QnAHandler(self.config.database_path, self.config.openrouter_key)
            
            response = self.handler.get_latest_summary()
            await update.message.reply_text(response, parse_mode='Markdown')
            
        except Exception as e:
            logger.error("Error getting latest videos", error=str(e))
            await update.message.reply_text("Sorry, I encountered an error retrieving the latest videos.")
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_text = """
🤖 **Q&A Bot Help**

**How to use:**
1. **Ask questions**: `/ask What is discussed in the latest video?`
2. **Search content**: `/search artificial intelligence`
3. **Get latest**: `/latest` - Shows recent video summaries
4. **Natural questions**: Just send a message without commands

**Tips:**
• Be specific with your questions
• Use keywords for better search results
• Ask about specific topics, people, or concepts
• Check latest videos to see what's available

The bot searches through all video summaries and subtitles to find relevant information!
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages."""
        question = update.message.text.strip()
        if question:
            await self._process_question(update, question)
    
    async def _process_question(self, update: Update, question: str):
        """Process a question and send response."""
        try:
            if not self.handler:
                self.handler = QnAHandler(self.config.database_path, self.config.openrouter_key)
            
            # Send typing indicator
            await update.message.chat.send_action("typing")
            
            # Process question
            response = self.handler.search_and_answer(question)
            
            # Send response
            await update.message.reply_text(response, parse_mode='Markdown')
            
        except Exception as e:
            logger.error("Error processing question", error=str(e))
            await update.message.reply_text(
                "Sorry, I encountered an error processing your question. Please try again."
            )
    
    async def _process_search(self, update: Update, query: str):
        """Process search query and send results."""
        try:
            if not self.handler:
                self.handler = QnAHandler(self.config.database_path, self.config.openrouter_key)
            
            # Send typing indicator
            await update.message.chat.send_action("typing")
            
            # Process search
            response = self.handler.search_content(query)
            
            # Send response
            await update.message.reply_text(response, parse_mode='Markdown')
            
        except Exception as e:
            logger.error("Error processing search", error=str(e))
            await update.message.reply_text(
                "Sorry, I encountered an error processing your search. Please try again."
            )
    
    def run(self):
        """Start the bot."""
        logger.info("Starting Q&A bot", channel_name=self.config.channel_name, database_path=self.config.database_path, chat_id=self.config.chat_id)
        
        self.application.run_polling()

def main():
    """Main entry point."""
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python bot.py <config_file.yml>")
        sys.exit(1)
    
    config_file = sys.argv[1]
    
    try:
        bot = QnABot(config_file)
        bot.run()
    except Exception as e:
        logger.error("Failed to start bot", error=str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()