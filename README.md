# yt2telegramRAG

A YouTube-to-Telegram RAG (Retrieval-Augmented Generation) system that:

- Monitors a YouTube channel for new videos
- Extracts transcripts and generates AI summaries
- Sends notifications to a Telegram chat
- Answers user questions about the channel's content using the latest transcript and all previous summaries

---

## Features

- No YouTube API key required (uses yt-dlp)
- Multi-language transcript support (Russian, German, English)
- All configuration via `.env` file
- SQLite database for persistent storage
- Logging to file and console
- Modular: monitor and bot run as separate scripts

---

## Setup

### 1. Clone & Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

- Copy `.env.example` to `.env` and fill in your secrets:
  - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `OPENAI_API_KEY`, `CHANNEL_ID`, `OPENAI_MODEL`, `OPENAI_MODEL_BOT`
- Never commit your real `.env` to git.

### 3. Database

- The SQLite database is created automatically on first run.
- Default path: `/root/youtube_monitor.db` (override with `DB_PATH` in `.env`)

---

## Usage

### Monitor Script (youtube_monitor.py)

- Processes up to 10 new videos per run
- Sends summaries to Telegram
- To run once (for cron):
  ```bash
  python3 youtube_monitor.py
  ```
- Example crontab (daily at 8am):
  ```
  0 8 * * * /usr/bin/python3 /path/to/yt2telegramRAG/youtube_monitor.py >> /path/to/yt2telegramRAG/monitor.log 2>&1
  ```

### Bot Script (bot.py)

- Listens for user questions in Telegram
- Answers using latest transcript and all previous summaries
- To run persistently:
  ```bash
  python3 bot.py
  ```
- Example systemd service:

  ```ini
  [Unit]
  Description=yt2telegramRAG Telegram Bot
  After=network.target

  [Service]
  Type=simple
  WorkingDirectory=/path/to/yt2telegramRAG
  ExecStart=/usr/bin/python3 /path/to/yt2telegramRAG/bot.py
  Restart=always
  User=youruser

  [Install]
  WantedBy=multi-user.target
  ```

---

## Logging & Monitoring

- Logs are written to `yt2telegramRAG.log` and `yt2telegramRAG-bot.log`.
- All errors and important actions are logged.
- For advanced monitoring, integrate with systemd journal, logrotate, or a cloud logging service.

---

## Security & Server Notes

- No inbound ports or SSL needed (all outbound HTTPS)
- Ensure outbound internet access is allowed
- Secure `.env` and database files (set correct permissions)
- Keep your system and Python packages up to date

---

## FAQ

**How do I get my Telegram bot token and chat ID?**

- Create a bot with [@BotFather](https://t.me/BotFather) and get the token.
- Add the bot to your chat/group, send a message, then use the Telegram API `/getUpdates` to find your chat ID.

**How do I change the OpenAI model?**

- Set `OPENAI_MODEL` and `OPENAI_MODEL_BOT` in your `.env` file.

**How do I add the bot to a new chat/group?**

- Add the bot to the group via Telegram, then update `TELEGRAM_CHAT_ID` in `.env`.

---

## Contributing

Pull requests and issues are welcome!

---

## License

MIT
