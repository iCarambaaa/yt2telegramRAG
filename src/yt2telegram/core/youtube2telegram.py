#!/usr/bin/env python3
# flake8: noqa
"""
YouTube Channel Monitor with Telegram Notifications
Runs once per invocation (ideal for cron).

Features
--------
* Fetches latest channel videos via yt‑dlp (no YouTube Data API key).
* Skips videos already processed using an on‑disk SQLite database.
* Extraction yt‑dlp subtitle download.
* Summarises via OpenAI ChatCompletion.
* Sends MarkdownV2‑formatted notifications to Telegram.

Environment variables required
-----------------------------
TELEGRAM_BOT_TOKEN   – Telegram bot token
TELEGRAM_CHAT_ID     – Chat/channel ID to post to
LLM_PROVIDER_API_KEY – OpenAI (or compatible) key
CHANNEL_ID           – YouTube channel ID

Optional variables
------------------
DB_PATH              – Path for the SQLite DB (default: ~/youtube_monitor.db)
OPENAI_BASE_URL      – Override for custom inference endpoint
OPENAI_MODEL         – Chat model name (default: gpt-4o-mini)
"""

from __future__ import annotations
from ratelimit import limits, sleep_and_retry

import logging
import os
import re
import sqlite3
import tempfile
from datetime import datetime
from typing import Dict, List

import yt_dlp
from dotenv import load_dotenv
from telegram import Bot
import openai
try:
    import yaml
except ImportError:
    raise ImportError("pyyaml is required for prompt loading. Install with: pip install pyyaml")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_DB_PATH = os.path.expanduser("~/youtube_monitor.db")
YOUTUBE_SUB_LANGS = ["de|ru|en"]
MAX_NEW_VIDEOS = 1
TELEGRAM_PARSE_MODE = "MarkdownV2"
SUMMARY_TEMPLATE = (
    "🎥 *New YouTube Video*\n\n"
    "*{title}*\n"
    "📅 Published: {published}\n\n"
    "{summary}\n\n"
    "🔗 https://www.youtube.com/watch?v={video_id}"
)

MD_V2_SPECIAL = r"_\*\[\]\(\)~`>#+\-=|{}\.!"

def escape_markdown_v2(text: str) -> str:
    """Escape Telegram‑MarkdownV2 special characters."""
    return re.sub(f"([{re.escape(MD_V2_SPECIAL)}])", r"\\\1", text)


# ---------------------------------------------------------------------------
# Configuration loader
# ---------------------------------------------------------------------------
class Config:
    def __init__(self) -> None:
        load_dotenv()
        self.telegram_bot_token: str | None = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id: str | None = os.getenv("TELEGRAM_CHAT_ID")
        self.openai_api_key: str | None = os.getenv("LLM_PROVIDER_API_KEY")
        self.channel_id: str | None = os.getenv("CHANNEL_ID")
        self.openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.db_path: str = os.getenv("DB_PATH", DEFAULT_DB_PATH)
        self.cookies_file: str | None = os.getenv("COOKIES_FILE")

        missing = [name for name in (
            "telegram_bot_token",
            "telegram_chat_id",
            "openai_api_key",
            "channel_id",
        ) if getattr(self, name) is None]
        if missing:
            raise ValueError(f"Missing required environment variables: {missing}")


# ---------------------------------------------------------------------------
# Database helper
# ---------------------------------------------------------------------------
class Database:
    def __init__(self, path: str) -> None:
        logging.info(f"Initializing database at: {path}")
        self.conn = sqlite3.connect(path)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS processed_videos (
                video_id TEXT PRIMARY KEY,
                title TEXT,
                published_at TEXT,
                processed_at TEXT,
                summary TEXT,
                subtitles TEXT
            )
            """
        )
        self.conn.commit()
        logging.info("Database initialized successfully")

    def is_processed(self, video_id: str) -> bool:
        logging.debug(f"Checking if video {video_id} is already processed")
        cur = self.conn.execute(
            "SELECT 1 FROM processed_videos WHERE video_id = ?", (video_id,)
        )
        result = cur.fetchone() is not None
        logging.debug(f"Video {video_id} processed status: {result}")
        return result

    def mark_processed(
        self,
        video_id: str,
        title: str,
        published_at: str,
        summary: str,
        subtitles: str,
    ) -> None:
        logging.info(f"Marking video {video_id} as processed in database")
        self.conn.execute(
            """
            INSERT INTO processed_videos (
                video_id, title, published_at, processed_at, summary, subtitles
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                video_id,
                title,
                published_at,
                datetime.utcnow().isoformat(),
                summary,
                subtitles,
            ),
        )
        self.conn.commit()
        logging.info(f"Successfully marked video {video_id} as processed")

    def close(self) -> None:
        logging.info("Closing database connection")
        self.conn.close()


# ---------------------------------------------------------------------------
# YouTube helpers
# ---------------------------------------------------------------------------
class YouTubeClient:
    def __init__(self, channel_id: str, cookies_file: str | None = None):
        logging.info(f"Initializing YouTube client for channel: {channel_id}")
        self.channel_id = channel_id
        self.cookies_file = cookies_file
        logging.info(f"Cookies file: {cookies_file}")

    def get_latest_videos(self) -> List[Dict]:
        """Return metadata for the latest MAX_NEW_VIDEOS uploads."""
        logging.info(f"Fetching latest videos from channel: {self.channel_id}")
        ydl_opts = {
            "extract_flat": True,
            "skip_download": True,
            "quiet": True,
        }
        
        if self.cookies_file and os.path.exists(self.cookies_file):
            logging.info(f"Using cookies file: {self.cookies_file}")
            ydl_opts["cookiefile"] = self.cookies_file
        
        channel_url = f"https://www.youtube.com/channel/{self.channel_id}/videos"
        logging.info(f"Fetching from URL: {channel_url}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logging.info("Extracting channel info...")
            info = ydl.extract_info(channel_url, download=False)
            entries = info.get("entries", [])
            logging.info(f"Found {len(entries)} total entries")

        videos = [
            {
                "video_id": e["id"],
                "title": e.get("title", ""),
                "published_at": e.get("upload_date", ""),
                "description": e.get("description", ""),
            }
            for e in entries[:MAX_NEW_VIDEOS]
        ]
        logging.info(f"Returning {len(videos)} latest videos")
        return videos


class SubtitleExtractor:
    """Extract subtitles directly via yt-dlp subtitle download."""

    def __init__(self, cookies_file: str | None = None):
        logging.info("Initializing SubtitleExtractor")
        self.cookies_file = cookies_file

    def get_subtitles(self, video_id: str) -> str | None:
        """Extract subtitles directly from YouTube videos."""
        logging.info(f"Starting subtitle extraction for video: {video_id}")
        temp_dir = tempfile.gettempdir()
        logging.info(f"Using temp directory: {temp_dir}")
        
        ydl_opts = {
           # "writesubtitles": True,
            "writeautomaticsub": True,
           # "subtitleslangs": YOUTUBE_SUB_LANGS,
            "skip_download": True,
            "outtmpl": os.path.join(temp_dir, f"{video_id}"),
            "quiet": True,
             
        }
        
        if self.cookies_file and os.path.exists(self.cookies_file):
            logging.info(f"Using cookies file for subtitle extraction: {self.cookies_file}")
            ydl_opts["cookiefile"] = self.cookies_file
        
        try:
            logging.info(f"Downloading subtitles for video: {video_id}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
            
            # Try to find and return subtitle content
            logging.info("Searching for subtitle files...")
            for lang in YOUTUBE_SUB_LANGS:
                for ext in ['vtt', 'srt']:
                    path = os.path.join(temp_dir, f"{video_id}.{lang}.{ext}")
                    logging.debug(f"Checking for subtitle file: {path}")
                    if os.path.exists(path):
                        try:
                            logging.info(f"Found subtitle file: {path}")
                            with open(path, "r", encoding="utf-8") as fh:
                                content = fh.read()
                            logging.info(f"Successfully read subtitle content, length: {len(content)} chars")
                            # Clean up the temporary file
                            os.remove(path)
                            logging.info("Cleaned up temporary subtitle file")
                            return content
                        except Exception as e:
                            logging.warning(f"Error reading subtitle file {path}: {e}")
                            if os.path.exists(path):
                                os.remove(path)
        except Exception as e:
            logging.warning(f"yt-dlp subtitle extraction error for {video_id}: {e}")
        logging.info(f"No subtitles found for video: {video_id}")
        return None


# ---------------------------------------------------------------------------
# Prompt loader
# ---------------------------------------------------------------------------
def load_prompt():
    prompt_file = os.getenv("YT2TG_PROMPT_FILE")
    if prompt_file and os.path.exists(prompt_file):
        with open(prompt_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            return data.get('summary_prompt')
    return None


# ---------------------------------------------------------------------------
# Summarization
# ---------------------------------------------------------------------------
class Summarizer:
    def __init__(self, api_key: str, base_url: str, model: str):
        logging.info(f"Initializing Summarizer with model: {model}")
        logging.info(f"Using API endpoint: {base_url}")
        self.client = openai.OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.prompt_template = load_prompt() or (
            "Analyze this YouTube video and provide a concise summary:\n\n"
            "Title: {title}\n"
            "Description: {description}\n"
            "Subtitles: {subtitles}\n\n"
            "Provide:\n"
            "1. Main topics\n"
            "2. Key points\n"
            "3. Important takeaways\n"
            "4. Relevant links mentioned\n"
            "5. Your opinion on the video's value\n\n"
            "Format as a Telegram‑friendly message with emojis."
        )
        logging.info("Summarizer initialized successfully")

    def summarize(
        self,
        title: str,
        description: str,
        subtitles: str,
        max_tokens: int = 300,
    ) -> str:
        logging.info(f"Starting summarization for video: {title}")
        logging.info(f"Description length: {len(description)} chars")
        logging.info(f"Subtitles length: {len(subtitles)} chars")
        logging.info(f"Max tokens for summary: {max_tokens}")
        
        prompt = self.prompt_template.format(title=title, description=description, subtitles=subtitles[:5000])
        logging.debug(f"Generated prompt length: {len(prompt)} chars")
        
        try:
            logging.info("Sending request to OpenAI API...")
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Summarize YouTube videos concisely."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
            )
            summary = resp.choices[0].message.content
            logging.info(f"Successfully generated summary, length: {len(summary)} chars")
            return summary
        except Exception as e:
            logging.error(f"OpenAI summarisation error: {e}")
            return "Summary unavailable."


# ---------------------------------------------------------------------------
# Telegram notifier
# ---------------------------------------------------------------------------
class Notifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot = Bot(token=bot_token)
        self.chat_id = chat_id

    def send(self, text: str) -> None:
        try:
            self.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=TELEGRAM_PARSE_MODE,
                disable_web_page_preview=False,
            )
        except Exception as e:
            logging.error(f"Telegram send error: {e}")


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("yt2telegramRAG.log"),
            logging.StreamHandler()
        ]
    )
    
    logging.info("=" * 60)
    logging.info("STARTING YOUTUBE TO TELEGRAM PIPELINE")
    logging.info("=" * 60)
    
    try:
        logging.info("Loading configuration...")
        cfg = Config()
        logging.info("Configuration loaded successfully")
        
        logging.info("Initializing components...")
        db = Database(cfg.db_path)
        yt = YouTubeClient(cfg.channel_id, cfg.cookies_file)
        se = SubtitleExtractor(cfg.cookies_file)
        summariser = Summarizer(cfg.openai_api_key, cfg.openai_base_url, cfg.openai_model)
        notifier = Notifier(cfg.telegram_bot_token, cfg.telegram_chat_id)
        logging.info("All components initialized successfully")
        
        logging.info("Fetching latest videos...")
        all_videos = yt.get_latest_videos()
        logging.info(f"Found {len(all_videos)} total videos from channel")
        
        new_videos = [
            v for v in all_videos if not db.is_processed(v["video_id"])
        ]
        logging.info(f"Found {len(new_videos)} new videos to process")
        
        if not new_videos:
            logging.info("No new videos found. Exiting.")
            db.close()
            return

        for idx, video in enumerate(new_videos, 1):
            logging.info("-" * 60)
            logging.info(f"Processing video {idx}/{len(new_videos)}")
            logging.info(f"Video ID: {video['video_id']}")
            logging.info(f"Title: {video['title']}")
            logging.info(f"Published: {video['published_at']}")
            
            logging.info("Extracting subtitles...")
            subtitles = se.get_subtitles(video["video_id"]) or video["description"]
            logging.info(f"Subtitles extracted, length: {len(subtitles)} chars")
            
            logging.info("Generating summary...")
            summary_raw = summariser.summarize(
                video["title"], video["description"], subtitles
            )
            logging.info("Summary generated successfully")

            logging.info("Formatting message for Telegram...")
            # Escape for MarkdownV2
            summary = escape_markdown_v2(summary_raw)
            title_md = escape_markdown_v2(video["title"])

            message = SUMMARY_TEMPLATE.format(
                title=title_md,
                published=escape_markdown_v2(video["published_at"]),
                summary=summary,
                video_id=video["video_id"],
            )
            logging.info("Message formatted successfully")
            logging.debug(f"Message content: {message}")

            logging.info("Sending message to Telegram...")
            notifier.send(message)
            logging.info("Message sent successfully")

            logging.info("Saving to database...")
            db.mark_processed(
                video["video_id"],
                video["title"],
                video["published_at"],
                summary_raw,
                subtitles,
            )
            logging.info("Video processing completed")

        logging.info("=" * 60)
        logging.info("PIPELINE COMPLETED SUCCESSFULLY")
        logging.info("=" * 60)
        
    except Exception as e:
        logging.error(f"Pipeline failed with error: {e}", exc_info=True)
        raise
    finally:
        logging.info("Closing database connection...")
        db.close()
        logging.info("Database connection closed")


if __name__ == "__main__":
    main()