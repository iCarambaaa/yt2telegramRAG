#!/usr/bin/env python3
"""
YouTube Channel Monitor with Telegram Notifications
Monitors a YouTube channel for new videos, extracts transcripts, 
uses AI to summarize content, and sends notifications via Telegram.
"""

import os
import sqlite3
import schedule
import time
from datetime import datetime
import yt_dlp
import openai
from telegram import Bot
from dotenv import load_dotenv
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("yt2telegramRAG.log"),
        logging.StreamHandler()
    ]
)

class YouTubeMonitor:
    def __init__(self):
        load_dotenv()
        self.config = self.load_config()
        self.db_path = os.getenv("DB_PATH", "/root/youtube_monitor.db")
        self.init_database()
        logging.info("YouTubeMonitor initialized.")
        
    def load_config(self):
        """Load configuration from environment variables"""
        return {
            "telegram_bot_token": os.getenv("TELEGRAM_BOT_TOKEN"),
            "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID"),
            "openai_api_key": os.getenv("LLM_PROVIDER_API_KEY"),
            "channel_id": os.getenv("CHANNEL_ID"),
            "openai_base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            "openai_model": os.getenv("OPENAI_MODEL" "gpt-4.1-2025-04-14")
        }
    
    def init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_videos (
                video_id TEXT PRIMARY KEY,
                title TEXT,
                published_at TEXT,
                processed_at TEXT,
                summary TEXT,
                transcript TEXT
            )
        ''')
        conn.commit()
        conn.close()
    
    def get_new_videos(self):
        """Fetch new videos from YouTube channel using yt-dlp (no API key needed)"""
        try:
            ydl_opts = {
                'extract_flat': True,
                'skip_download': True,
                'quiet': True,
            }
            channel_url = f"https://www.youtube.com/channel/{self.config['channel_id']}/videos"
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(channel_url, download=False)
                entries = info.get('entries', [])
            new_videos = []
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            for entry in entries[:10]:  # Only check the latest 10 videos
                video_id = entry['id']
                cursor.execute('SELECT video_id FROM processed_videos WHERE video_id = ?', (video_id,))
                if cursor.fetchone() is None:
                    new_videos.append({
                        'video_id': video_id,
                        'title': entry.get('title', ''),
                        'published_at': entry.get('upload_date', ''),
                        'description': entry.get('description', '')
                    })
            conn.close()
            logging.info(f"Found {len(new_videos)} new videos.")
            return new_videos
        except Exception as e:
            logging.error(f"yt-dlp error: {e}")
            return []
    
    def get_video_transcript(self, video_id):
        """Get video transcript using yt-dlp, stick to original language if Russian or German, else use English."""
        try:
            ydl_opts = {
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'outtmpl': f'/tmp/{video_id}.%(ext)s',
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
                subtitles = info.get('subtitles', {})
                automatic_captions = info.get('automatic_captions', {})
                # Detect original language
                original_lang = info.get('language', '')
                # Fallback: try to detect from available subtitles
                available_langs = list(subtitles.keys()) + list(automatic_captions.keys())
                if 'ru' in available_langs:
                    chosen_lang = 'ru'
                elif 'de' in available_langs:
                    chosen_lang = 'de'
                elif 'en' in available_langs:
                    chosen_lang = 'en'
                else:
                    chosen_lang = available_langs[0] if available_langs else None
                if chosen_lang:
                    if chosen_lang in subtitles:
                        return subtitles[chosen_lang][0]['url']
                    elif chosen_lang in automatic_captions:
                        return automatic_captions[chosen_lang][0]['url']
                return None
        except Exception as e:
            logging.error(f"Error getting transcript: {e}")
            return None
    
    def extract_essential_info(self, transcript, title, description):
        """Use OpenAI to extract essential information"""
        try:
            client = openai.OpenAI(
                api_key=self.config['openai_api_key'],
                base_url=self.config.get('openai_base_url', 'https://api.openai.com/v1')
            )
            
            prompt = f"""
            Analyze this YouTube video and provide a concise summary:
            
            Title: {title}
            Description: {description}
            Transcript: {transcript[:4000]}
            
            Provide:
            1. Main topics
            2. key points
            3. all important takeaways
            4. any relevant links or resources mentioned
            5. your opinion on the video's value
            
            Format as Telegram-friendly message with emojis.
            """
            
            response = client.chat.completions.create(
                model=self.config["openai_model"],
                messages=[
                    {"role": "system", "content": "Summarize YouTube videos concisely."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300
            )
            
            logging.info(f"Summary generated for video: {title}")
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"OpenAI summary error: {str(e)}")
            return f"Summary unavailable: {str(e)}"
    
    def send_telegram_message(self, message):
        """Send message via Telegram bot"""
        try:
            bot = Bot(token=self.config['telegram_bot_token'])
            bot.send_message(
                chat_id=self.config['telegram_chat_id'],
                text=message,
                parse_mode='Markdown'
            )
            logging.info("Telegram message sent.")
        except Exception as e:
            logging.error(f"Telegram error: {e}")
    
    def mark_video_processed(self, video, summary, transcript):
        """Mark video as processed and store transcript"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO processed_videos (video_id, title, published_at, processed_at, summary, transcript)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            video['video_id'],
            video['title'],
            video['published_at'],
            datetime.now().isoformat(),
            summary,
            transcript
        ))
        conn.commit()
        conn.close()
        logging.info(f"Video marked as processed: {video['title']}")
    
    def process_new_videos(self):
        """Process up to 10 new videos"""
        logging.info("Checking for new videos...")
        new_videos = self.get_new_videos()
        
        if not new_videos:
            logging.info("No new videos found.")
            return
        
        # Only process up to 10 new videos
        for video in new_videos[:10]:
            logging.info(f"Processing video: {video['title']}")
            
            transcript = self.get_video_transcript(video['video_id'])
            if not transcript:
                transcript = video['description']
            
            summary = self.extract_essential_info(transcript, video['title'], video['description'])
            
            message = f"""🎥 **New YouTube Video**

**{video['title']}**
📅 Published: {video['published_at']}

{summary}

🔗 https://www.youtube.com/watch?v={video['video_id']}"""
            
            self.send_telegram_message(message)
            self.mark_video_processed(video, summary, transcript)
            logging.info(f"✅ Sent: {video['title']}")
    
    def run_scheduler(self):
        """Run the scheduler"""
        schedule.every(self.config.get('check_interval_hours', 24)).hours.do(self.process_new_videos)
        
        logging.info("YouTube Monitor started...")
        self.process_new_videos()  # Run once immediately
        
        while True:
            schedule.run_pending()
            time.sleep(3600)

if __name__ == "__main__":
    monitor = YouTubeMonitor()
    monitor.process_new_videos()