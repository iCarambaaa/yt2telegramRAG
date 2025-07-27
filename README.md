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
- Prompts are separated into YAML files for easy editing (`prompts/` directory)
- SQLite database for persistent storage
- Logging to file and console
- Modular: monitor and bot run as separate scripts
- Proper Python package structure

---

## Project Structure

```
yt2telegramRAG/
├── src/
│   └── yt2telegram/
│       ├── __init__.py
│       ├── __main__.py
│       ├── core/
│       │   ├── __init__.py
│       │   └── youtube2telegram.py
│       ├── bot/
│       │   ├── __init__.py
│       │   └── tg_bot.py
│       ├── db/
│       │   ├── __init__.py
│       │   └── database.py
│       └── utils/
│           ├── __init__.py
│           ├── subtitle_downloader.py
│           ├── test_subtitles.py
│           └── extract_clean_subtitles.py
├── prompts/
│   ├── Robyn/
│   │   ├── robynHD_y2t.yml
│   │   └── robyn_tg_bot.yml
│   ├── tg_bot.yml
│   └── youtube2telegram.yml
├── DBs/
│   └── robyn.db
├── downloads/
├── tests/
├── .env
├── .env.example
├── requirements.txt
├── setup.py
├── README.md
└── ...
```

---

## Setup

### 1. Clone & Install Dependencies

```bash
pip install -r requirements.txt
```

Or install as a package:

```bash
pip install -e .
```

### 2. Configure Environment

- Copy `.env.example` to `.env` and fill in your secrets:
  - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `LLM_PROVIDER_API_KEY`, `CHANNEL_ID`, `OPENAI_MODEL`, `OPENAI_MODEL_BOT`
  - Set `YOUTUBE2TELEGRAM_PROMPT_FILE` and `TG_BOT_PROMPT_FILE` to point to your YAML prompt files (see `prompts/` directory)
- Never commit your real `.env` to git.

### 3. Database

- The SQLite database is created automatically on first run.
- Default path: `./DBs/robyn.db` (override with `DB_PATH` in `.env`)

---

## Usage

### As a Package

After installing with `pip install -e .`:

```bash
# Monitor for new videos
yt2telegram monitor

# Run the Telegram bot
yt2telegram bot

# Download subtitles for a specific video
yt2telegram download-subtitles --video-id VIDEO_ID

# Test subtitle extraction for a specific video
yt2telegram test-subtitles --video-id VIDEO_ID

# Extract clean subtitles for a specific video
yt2telegram extract-subtitles --video-id VIDEO_ID
```

### Direct Script Execution

```bash
# Monitor for new videos
python -m src.yt2telegram.core.youtube2telegram

# Run the Telegram bot
python -m src.yt2telegram.bot.tg_bot

# Download subtitles for a specific video
python -m src.yt2telegram.utils.subtitle_downloader VIDEO_ID

# Test subtitle extraction for a specific video
python -m src.yt2telegram.utils.test_subtitles VIDEO_ID

# Extract clean subtitles for a specific video
python -m src.yt2telegram.utils.extract_clean_subtitles VIDEO_ID
```

### Monitor Script (`youtube2telegram.py`)

- Processes up to 10 new videos per run
- Sends summaries to Telegram
- To run once (for cron):
  ```bash
  yt2telegram monitor
  ```
- Example crontab (daily at 8am):
  ```
  0 8 * * * /usr/bin/yt2telegram monitor >> /path/to/yt2telegramRAG/monitor.log 2>&1
  ```

### Bot Script (`tg_bot.py`)

- Listens for user questions in Telegram
- Answers using latest transcript and all previous summaries
- To run persistently:
  ```bash
  yt2telegram bot
  ```
- Example systemd service:

  ```ini
  [Unit]
  Description=yt2telegramRAG Telegram Bot
  After=network.target

  [Service]
  Type=simple
  WorkingDirectory=/path/to/yt2telegramRAG
  ExecStart=/usr/bin/yt2telegram bot
  Restart=always
  User=youruser

  [Install]
  WantedBy=multi-user.target
  ```

---

## Prompts

- Prompts for both scripts are stored in YAML files in the `prompts/` directory.
- Set the environment variables `YOUTUBE2TELEGRAM_PROMPT_FILE` and `TG_BOT_PROMPT_FILE` to point to these files.
- Example YAML for `prompts/youtube2telegram.yml`:

  ```yaml
  summary_prompt: |
    Analyze this YouTube video and provide a concise summary:
    ...
  ```

  - Example YAML for `prompts/bot.yml`:

  ```yaml
  qa_prompt: |
    You are a helpful assistant for a YouTube-to-Telegram RAG bot.
    ...
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
