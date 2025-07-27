#!/usr/bin/env python3
"""
Telegram bot for Q&A functionality using RAG (Retrieval-Augmented Generation)
"""

import logging
import os
import sqlite3
from typing import List, Dict, Optional
import asyncio
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from dotenv import load_dotenv
import openai
from openai import OpenAI
import tiktoken

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
LLM_PROVIDER_API_KEY = os.getenv("LLM_PROVIDER_API_KEY")
DB_PATH = os.getenv("DB_PATH", os.path.expanduser("~/youtube_monitor.db"))
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MAX_CONTEXT_LENGTH = 4000
MAX_VIDEOS = 5

# Initialize OpenAI client
client = OpenAI(api_key=LLM_PROVIDER_API_KEY, base_url=OPENAI_BASE_URL)

class RAGDatabase:
    """Database interface for RAG functionality"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
    
    def connect(self):
        """Establish database connection"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def search_videos(self, query: str, limit: int = MAX_VIDEOS) -> List[Dict]:
        """Search videos by title or summary"""
        if not self.conn:
            self.connect()
        
        cursor = self.conn.cursor()
        
        # Search in both title and summary
        sql = """
        SELECT video_id, title, summary, subtitles, published_at, processed_at
        FROM processed_videos
        WHERE title LIKE ? OR summary LIKE ? OR subtitles LIKE ?
        ORDER BY published_at DESC
        LIMIT ?
        """
        
        search_term = f"%{query}%"
        cursor.execute(sql, (search_term, search_term, search_term, limit))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "video_id": row["video_id"],
                "title": row["title"],
                "summary": row["summary"],
                "subtitles": row["subtitles"],
                "published_at": row["published_at"],
                "processed_at": row["processed_at"]
            })
        
        return results
    
    def get_recent_videos(self, limit: int = MAX_VIDEOS) -> List[Dict]:
        """Get most recent videos"""
        if not self.conn:
            self.connect()
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT video_id, title, summary, subtitles, published_at, processed_at
            FROM processed_videos
            ORDER BY published_at DESC
            LIMIT ?
        """, (limit,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "video_id": row["video_id"],
                "title": row["title"],
                "summary": row["summary"],
                "subtitles": row["subtitles"],
                "published_at": row["published_at"],
                "processed_at": row["processed_at"]
            })
        
        return results
    
    def get_video_by_id(self, video_id: str) -> Optional[Dict]:
        """Get specific video by ID"""
        if not self.conn:
            self.connect()
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT video_id, title, summary, subtitles, published_at, processed_at
            FROM processed_videos
            WHERE video_id = ?
        """, (video_id,))
        
        row = cursor.fetchone()
        if row:
            return {
                "video_id": row["video_id"],
                "title": row["title"],
                "summary": row["summary"],
                "subtitles": row["subtitles"],
                "published_at": row["published_at"],
                "processed_at": row["processed_at"]
            }
        return None

class RAGProcessor:
    """RAG processor for generating answers"""
    
    def __init__(self, model: str = OPENAI_MODEL):
        self.model = model
        self.encoding = tiktoken.encoding_for_model(model)
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.encoding.encode(text))
    
    def truncate_text(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit within token limit"""
        tokens = self.encoding.encode(text)
        if len(tokens) <= max_tokens:
            return text
        
        # Truncate and add ellipsis
        truncated = self.encoding.decode(tokens[:max_tokens-3])
        return truncated + "..."
    
    def create_context(self, videos: List[Dict], query: str) -> str:
        """Create context from video data"""
        context_parts = []
        
        for video in videos:
            # Format date
            try:
                date = datetime.fromisoformat(video["published_at"].replace('Z', '+00:00'))
                formatted_date = date.strftime("%Y-%m-%d")
            except:
                formatted_date = video["published_at"]
            
            # Build context entry
            context_entry = f"""
Video: {video["title"]} ({formatted_date})
Summary: {video["summary"]}
Subtitles: {video["subtitles"][:1000]}...
Video ID: {video["video_id"]}
---
"""
            context_parts.append(context_entry)
        
        return "\n".join(context_parts)
    
    def generate_answer(self, query: str, context: str) -> str:
        """Generate answer using RAG"""
        system_prompt = """You are a helpful assistant that answers questions about YouTube videos based on their summaries and subtitles. 
Use the provided context to give accurate, relevant answers. If the context doesn't contain enough information, say so.
Be concise but informative."""
        
        user_prompt = f"""Based on the following video information, please answer: {query}

Context:
{context}

Answer:"""
        
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return "Sorry, I encountered an error while generating the answer."

class TelegramBot:
    """Main Telegram bot class"""
    
    def __init__(self):
        self.db = RAGDatabase(DB_PATH)
        self.processor = RAGProcessor()
        self.app = None
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = """
🤖 *YouTube RAG Bot*

Welcome! I can help you search and ask questions about YouTube videos that have been processed.

Available commands:
• /search <query> - Search for videos
• /recent - Show recent videos
• /ask <question> - Ask a question about videos
• /help - Show this help message

Just send me a message and I'll search through the video database to find relevant information!
"""
        
        await update.message.reply_text(welcome_message, parse_mode="Markdown")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
📋 *Available Commands:*

• `/search <query>` - Search for videos by title, summary, or content
  Example: `/search python tutorial`

• `/recent` - Show the most recent videos

• `/ask <question>` - Ask a question about the videos
  Example: `/ask What are the main topics covered in recent videos?`

• `/video <video_id>` - Get details about a specific video
  Example: `/video abc123xyz`

Just send a regular message and I'll search for relevant videos!
"""
        
        await update.message.reply_text(help_text, parse_mode="Markdown")
    
    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /search command"""
        query = " ".join(context.args)
        if not query:
            await update.message.reply_text("Please provide a search query. Example: `/search python tutorial`", parse_mode="Markdown")
            return
        
        await self.handle_search(update, query)
    
    async def recent_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /recent command"""
        try:
            videos = self.db.get_recent_videos()
            if not videos:
                await update.message.reply_text("No videos found in the database.")
                return
            
            message = "📺 *Recent Videos:*\n\n"
            for video in videos:
                try:
                    date = datetime.fromisoformat(video["published_at"].replace('Z', '+00:00'))
                    formatted_date = date.strftime("%Y-%m-%d")
                except:
                    formatted_date = video["published_at"]
                
                message += f"• [{video['title']}](https://www.youtube.com/watch?v={video['video_id']}) ({formatted_date})\n"
            
            await update.message.reply_text(message, parse_mode="Markdown", disable_web_page_preview=True)
            
        except Exception as e:
            logger.error(f"Error in recent command: {e}")
            await update.message.reply_text("Sorry, I encountered an error while fetching recent videos.")
    
    async def ask_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ask command"""
        question = " ".join(context.args)
        if not question:
            await update.message.reply_text("Please provide a question. Example: `/ask What are the main topics?`", parse_mode="Markdown")
            return
        
        await self.handle_question(update, question)
    
    async def video_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /video command"""
        video_id = " ".join(context.args)
        if not video_id:
            await update.message.reply_text("Please provide a video ID. Example: `/video abc123xyz`", parse_mode="Markdown")
            return
        
        try:
            video = self.db.get_video_by_id(video_id)
            if not video:
                await update.message.reply_text(f"Video with ID `{video_id}` not found.", parse_mode="Markdown")
                return
            
            try:
                date = datetime.fromisoformat(video["published_at"].replace('Z', '+00:00'))
                formatted_date = date.strftime("%Y-%m-%d")
            except:
                formatted_date = video["published_at"]
            
            message = f"""
📺 *{video['title']}*

📅 Published: {formatted_date}
🔗 [Watch on YouTube](https://www.youtube.com/watch?v={video['video_id']})

📋 *Summary:*
{video['summary']}

💬 *Subtitles (first 500 chars):*
{video['subtitles'][:500]}...
"""
            
            await update.message.reply_text(message, parse_mode="Markdown", disable_web_page_preview=True)
            
        except Exception as e:
            logger.error(f"Error in video command: {e}")
            await update.message.reply_text("Sorry, I encountered an error while fetching the video.")
    
    async def handle_search(self, update: Update, query: str):
        """Handle search queries"""
        try:
            videos = self.db.search_videos(query)
            if not videos:
                await update.message.reply_text(f"No videos found for query: `{query}`", parse_mode="Markdown")
                return
            
            message = f"🔍 *Search Results for:* `{query}`\n\n"
            for video in videos:
                try:
                    date = datetime.fromisoformat(video["published_at"].replace('Z', '+00:00'))
                    formatted_date = date.strftime("%Y-%m-%d")
                except:
                    formatted_date = video["published_at"]
                
                message += f"• [{video['title']}](https://www.youtube.com/watch?v={video['video_id']}) ({formatted_date})\n"
            
            await update.message.reply_text(message, parse_mode="Markdown", disable_web_page_preview=True)
            
        except Exception as e:
            logger.error(f"Error in search: {e}")
            await update.message.reply_text("Sorry, I encountered an error while searching.")
    
    async def handle_question(self, update: Update, question: str):
        """Handle questions using RAG"""
        try:
            # Search for relevant videos
            videos = self.db.search_videos(question)
            if not videos:
                await update.message.reply_text("I couldn't find any relevant videos to answer your question.")
                return
            
            # Create context and generate answer
            context = self.processor.create_context(videos, question)
            answer = self.processor.generate_answer(question, context)
            
            # Send answer
            message = f"❓ *Question:* {question}\n\n"
            message += f"🤖 *Answer:* {answer}\n\n"
            message += f"📊 *Based on {len(videos)} relevant video(s)*"
            
            await update.message.reply_text(message, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error handling question: {e}")
            await update.message.reply_text("Sorry, I encountered an error while processing your question.")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular messages as search queries"""
        text = update.message.text
        if text and not text.startswith("/"):
            await self.handle_search(update, text)
    
    def run(self):
        """Run the bot"""
        if not TELEGRAM_BOT_TOKEN:
            logger.error("TELEGRAM_BOT_TOKEN not set")
            return
        
        logger.info("Starting Telegram bot...")
        self.app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Add handlers
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("search", self.search_command))
        self.app.add_handler(CommandHandler("recent", self.recent_command))
        self.app.add_handler(CommandHandler("ask", self.ask_command))
        self.app.add_handler(CommandHandler("video", self.video_command))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Start the bot
        logger.info("Bot started successfully!")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    bot = TelegramBot()
    bot.run()