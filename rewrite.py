#!/usr/bin/env python3
"""
YouTube Channel Monitor with Telegram Notifications
Runs once per invocation (ideal for cron).

Features
--------
* Fetches latest channel videos via yt‑dlp (no YouTube Data API key).
* Skips videos already processed using an on‑disk SQLite database.
* Transcript extraction prefers YouTubeTranscriptApi; falls back to
  yt‑dlp subtitle download when necessary.
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

import logging
import os
import re
import sqlite3
from datetime import datetime
from typing import Dict, List

import yt_dlp
from dotenv import load_dotenv
from telegram import Bot
from youtube_transcript_api import NoTranscriptFound, TranscriptsDisabled, YouTubeTranscriptApi
import openai

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_DB_PATH = os.path.expanduser("~/youtube_monitor.db")
YOUTUBE_SUB_LANGS = ["ru", "de", "en"]
MAX_NEW_VIDEOS = 10
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
        self.conn = sqlite3.connect(path)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS processed_videos (
                video_id TEXT PRIMARY KEY,
                title TEXT,
                published_at TEXT,
                processed_at TEXT,
                summary TEXT,
                transcript TEXT
            )
            """
        )
        self.conn.commit()

    def is_processed(self, video_id: str) -> bool:
        cur = self.conn.execute(
            "SELECT 1 FROM processed_videos WHERE video_id = ?", (video_id,)
        )
        return cur.fetchone() is not None

    def mark_processed(
        self,
        video_id: str,
        title: str,
        published_at: str,
        summary: str,
        transcript: str,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO processed_videos (
                video_id, title, published_at, processed_at, summary, transcript
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                video_id,
                title,
                published_at,
                datetime.utcnow().isoformat(),
                summary,
                transcript,
            ),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()


# ---------------------------------------------------------------------------
# YouTube helpers
# ---------------------------------------------------------------------------
class YouTubeClient:
    def __init__(self, channel_id: str):
        self.channel_id = channel_id

    def get_latest_videos(self) -> List[Dict]:
        """Return metadata for the latest MAX_NEW_VIDEOS uploads."""
        ydl_opts = {
            "extract_flat": True,
            "skip_download": True,
            "quiet": True,
        }
        channel_url = f"https://www.youtube.com/channel/{self.channel_id}/videos"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
            entries = info.get("entries", [])

        return [
            {
                "video_id": e["id"],
                "title": e.get("title", ""),
                "published_at": e.get("upload_date", ""),
                "description": e.get("description", ""),
            }
            for e in entries[:MAX_NEW_VIDEOS]
        ]


class TranscriptExtractor:
    """Obtain a transcript via Transcript API first, yt‑dlp fallback second."""

    @staticmethod
    def from_api(video_id: str) -> str | None:
        try:
            segments = YouTubeTranscriptApi.get_transcript(
                video_id, languages=YOUTUBE_SUB_LANGS
            )
            return " ".join(seg["text"] for seg in segments)
        except (TranscriptsDisabled, NoTranscriptFound):
            return None
        except Exception as e:
            logging.warning(f"Transcript API error for {video_id}: {e}")
            return None

    @staticmethod
    def from_ytdlp(video_id: str) -> str | None:
        ydl_opts = {
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": YOUTUBE_SUB_LANGS,
            "skip_download": True,
            "outtmpl": f"/tmp/{video_id}",
            "quiet": True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
            for lang in YOUTUBE_SUB_LANGS:
                path = f"/tmp/{video_id}.{lang}.vtt"
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as fh:
                        vtt = fh.read()
                    os.remove(path)
                    return TranscriptExtractor._parse_vtt(vtt)
        except Exception as e:
            logging.warning(f"yt-dlp subtitle error for {video_id}: {e}")
        return None

    @staticmethod
    def _parse_vtt(vtt: str) -> str:
        lines: List[str] = []
        for line in vtt.splitlines():
            line = line.strip()
            if (
                not line
                or line.startswith("WEBVTT")
                or re.match(r"^\d+$", line)
                or re.match(r"^\d{2}:\d{2}:\d{2}\.\d{3} -->", line)
                or re.match(r"^\d{2}:\d{2}\.\d{3} -->", line)
            ):
                continue
            lines.append(line)
        return " ".join(lines)

    def get_transcript(self, video_id: str) -> str | None:
        return self.from_api(video_id) or self.from_ytdlp(video_id)


# ---------------------------------------------------------------------------
# Summarisation
# ---------------------------------------------------------------------------
class Summarizer:
    def __init__(self, api_key: str, base_url: str, model: str):
        self.client = openai.OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def summarize(
        self,
        title: str,
        description: str,
        transcript: str,
        max_tokens: int = 300,
    ) -> str:
        prompt = (
            "Analyze this YouTube video and provide a concise summary:\n\n"
            f"Title: {title}\n"
            f"Description: {description}\n"
            f"Transcript: {transcript[:4000]}\n\n"
            "Provide:\n"
            "1. Main topics\n"
            "2. Key points\n"
            "3. Important takeaways\n"
            "4. Relevant links mentioned\n"
            "5. Your opinion on the video's value\n\n"
            "Format as a Telegram‑friendly message with emojis."
        )
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Summarize YouTube videos concisely."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content
        except Exception as e:
            logging.error(f"OpenAI summarisation error: {e}")
            return "Summary unavailable."""


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
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    cfg = Config()
    db = Database(cfg.db_path)
    yt = YouTubeClient(cfg.channel_id)
    tx = TranscriptExtractor()
    summariser = Summarizer(cfg.openai_api_key, cfg.openai_base_url, cfg.openai_model)
    notifier = Notifier(cfg.telegram_bot_token, cfg.telegram_chat_id)

    new_videos = [
        v for v in yt.get_latest_videos() if not db.is_processed(v["video_id"])
    ]
    logging.info(f"Found {len(new_videos)} new videos.")

    for video in new_videos:
        logging.info(f"Processing {video['title']}")
        transcript = tx.get_transcript(video["video_id"]) or video["description"]
        summary_raw = summariser.summarize(
            video["title"], video["description"], transcript
        )

        # Escape for MarkdownV2
        summary = escape_markdown_v2(summary_raw)
        title_md = escape_markdown_v2(video["title"])

        message = SUMMARY_TEMPLATE.format(
            title=title_md,
            published=escape_markdown_v2(video["published_at"]),
            summary=summary,
            video_id=video["video_id"],
        )

        notifier.send(message)
        db.mark_processed(
            video["video_id"],
            video["title"],
            video["published_at"],
            summary_raw,
            transcript,
        )
        logging.info("Done.")

    db.close()


if __name__ == "__main__":
    main()
