# YouTube to Telegram Channel Manager

- Monitors YouTube channels for new videos
- Downloads and cleans video transcripts  
- Generates AI-powered summaries
- Sends notifications to Telegram chats
- Includes Q&A bot functionality for channel content

**Key Features:**
- ✅ Sequential processing
- ✅ Clean architecture with services/models/utils
- ✅ Error handling and logging
- ✅ Minimal dependencies
- ✅ Production-ready reliability

---

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Setup Cookies (Important!)
```bash
# Copy the template
cp COOKIES_FILE.example COOKIES_FILE

# Add your YouTube cookies to COOKIES_FILE
# Use browser extensions like "Get cookies.txt" to export your YouTube session
```

### 3. Configure Environment
```bash
# Copy and edit environment variables
cp .env.example .env
# Edit .env with your API keys and tokens
```

### 4. Run
```bash
python run.py
```

---

## Project Structure

```
yt2telegram/
├── main.py                 # Main entry point
├── models/                 # Data models
│   ├── video.py           # Video data structure
│   └── channel.py         # Channel configuration
├── services/              # Core business logic
│   ├── youtube_service.py # YouTube API & downloads
│   ├── telegram_service.py# Telegram notifications
│   ├── database_service.py# SQLite operations
│   └── llm_service.py     # AI summarization
├── utils/                 # Helper functions
│   ├── subtitle_cleaner.py
│   ├── validators.py
│   └── logging_config.py
├── channels/              # Channel configurations
│   ├── example_channel.yml
│   └── your_channels.yml
└── qna/                   # Q&A bot functionality
```

---

## Configuration

### Channel Configuration
Create YAML files in `yt2telegram/channels/`:

```yaml
name: "Your Channel"
channel_id: "UCxxxxxxxxxxxxxxxxxx"
schedule: "daily"  # daily, weekly, monthly
db_path: "yt2telegram/downloads/your_channel.db"
cookies_file: "COOKIES_FILE"
max_videos_to_fetch: 5

llm_config:
  llm_api_key_env: "LLM_PROVIDER_API_KEY"
  llm_model: "gpt-4o-mini"
  llm_base_url: "https://openrouter.ai/api/v1"
  llm_prompt_template_path: "yt2telegram/prompts/your_prompt.md"

telegram_bots:
  - name: "Your Bot"
    token_env: "TELEGRAM_BOT_TOKEN"
    chat_id_env: "TELEGRAM_CHAT_ID"

subtitles:
  - lang: "en"
    type: "manual"
  - lang: "en" 
    type: "automatic"
```

### Environment Variables (.env)
```bash
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# LLM Provider (OpenRouter, OpenAI, etc.)
LLM_PROVIDER_API_KEY=your_api_key
MODEL=gpt-4o-mini
BASE_URL=https://openrouter.ai/api/v1
```

---

## Cookie Setup (Critical!)

The `COOKIES_FILE` is essential for accessing age-restricted or private YouTube content:

1. **Install a cookie export extension:**
   - Chrome: "Get cookies.txt" or "cookies.txt"
   - Firefox: "Export Cookies"

2. **Export your YouTube cookies:**
   - Go to youtube.com and ensure you're logged in
   - Use the extension to export cookies in Netscape format
   - Save as `COOKIES_FILE` in the project root

3. **Security:** The `COOKIES_FILE` contains your login session - keep it secure!

---

## Features

### ✅ **Sequential Processing**
- No async complexity - easier to debug
- Clear execution flow
- Better error handling
- Reliable retry logic

### ✅ **Clean Architecture** 
- Separated concerns (models, services, utils)
- Easy to test and maintain
- Modular design

### ✅ **Production Ready**
- Comprehensive logging
- Database persistence
- Error recovery
- Configurable retry attempts

### ✅ **Multi-Channel Support**
- Monitor multiple YouTube channels
- Individual configurations per channel
- Separate databases and schedules

---

## Deployment

### Cron Job (Recommended)
```bash
# Run every hour
0 * * * * cd /path/to/project && python run.py >> logs/cron.log 2>&1
```

### Systemd Service
```ini
[Unit]
Description=YouTube to Telegram Channel Manager
After=network.target

[Service]
Type=oneshot
WorkingDirectory=/path/to/project
ExecStart=/usr/bin/python3 run.py
User=your_user

[Install]
WantedBy=multi-user.target
```

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "run.py"]
```

---

## Dependencies

Minimal and focused:
- `python-dotenv` - Environment variables
- `yt-dlp` - YouTube downloading
- `openai` - LLM integration  
- `requests` - HTTP requests
- `pyyaml` - Configuration files

---

## Troubleshooting

### Common Issues

**"No videos found"**
- Check your `COOKIES_FILE` is properly configured
- Verify the YouTube channel ID is correct
- Ensure you have internet connectivity

**"LLM API Error"**  
- Verify your API key in `.env`
- Check your API provider's rate limits
- Ensure the model name is correct

**"Telegram send failed"**
- Verify bot token and chat ID
- Check if bot is added to the chat/group
- Ensure bot has send message permissions

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python run.py
```

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

---

## License

MIT License - see LICENSE file for details.