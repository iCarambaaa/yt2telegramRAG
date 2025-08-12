# YouTube to Telegram Channel Manager

Automatically monitors YouTube channels, generates AI-powered summaries that preserve each creator's unique style, and sends them to Telegram.

**Key Features:**
- ✅ **Smart Channel Setup** - Automated channel analysis and configuration
- ✅ **Style-Preserving Summaries** - Maintains each creator's unique voice and perspective  
- ✅ **Sequential Processing** - Reliable, easy-to-debug architecture
- ✅ **Multi-Language Support** - Uses original language captions automatically
- ✅ **Production Ready** - Comprehensive error handling and logging

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

### 4. Add a Channel (Smart Setup)
```bash
# Automatically analyze and setup any YouTube channel
python add_channel_smart.py UCbfYPyITQ-7l4upoX8nvctg
```

### 5. Run
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

## Smart Channel Setup

The `add_channel_smart.py` tool automatically analyzes YouTube channels and creates optimized configurations:

```bash
# Add any YouTube channel
python add_channel_smart.py <CHANNEL_ID>

# Example: Add Two Minute Papers
python add_channel_smart.py UCbfYPyITQ-7l4upoX8nvctg
```

**What it does:**
- 🔍 **Analyzes** recent videos to understand content style and themes
- 📝 **Generates** personalized prompts that preserve the creator's unique voice
- ⚙️ **Creates** optimized channel configuration automatically
- 🌍 **Detects** original language and uses appropriate captions
- 📅 **Recommends** posting schedule based on content type

### Manual Channel Configuration
You can also create YAML files manually in `yt2telegram/channels/`:

```yaml
name: "Your Channel"
channel_id: "UCxxxxxxxxxxxxxxxxxx"
schedule: "daily"  # daily, weekly, monthly
db_path: "yt2telegram/downloads/your_channel.db"
cookies_file: "COOKIES_FILE"
max_videos_to_fetch: 3

llm_config:
  llm_api_key_env: "LLM_PROVIDER_API_KEY"
  llm_model: "gpt-4o-mini"
  llm_base_url: "https://openrouter.ai/api/v1"
  llm_prompt_template_path: "yt2telegram/prompts/your_prompt.md"

telegram_bots:
  - name: "Your Bot"
    token_env: "TELEGRAM_BOT_TOKEN"
    chat_id_env: "YOUR_CHANNEL_CHAT_ID"

subtitles: ["en"]
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

## Key Features

### 🧠 **Style-Preserving AI Summaries**
- Maintains each creator's unique voice, humor, and perspective
- Extracts key facts while preserving storytelling approach
- Works with any content type: tech, crypto, geopolitics, science

### 🚀 **Smart Channel Setup**
- Automated channel analysis and configuration
- Detects content themes, style, and tone automatically
- Generates personalized prompts for each creator
- Uses original language captions automatically

### ⚡ **Sequential Processing**
- No async complexity - easier to debug and maintain
- Clear execution flow with comprehensive error handling
- Reliable retry logic and graceful failure recovery

### 🏗️ **Clean Architecture** 
- Separated concerns (models, services, utils)
- Easy to test, maintain, and extend
- Modular design with minimal dependencies

### 🌍 **Multi-Channel & Multi-Language**
- Monitor unlimited YouTube channels simultaneously
- Individual configurations and schedules per channel
- Automatic original language caption detection
- Separate databases and processing pipelines

---

## Example Channels

The project includes several pre-configured channels that demonstrate different content types and styles:

- **Isaac Arthur** - Space technology and megastructures with grand cosmic storytelling
- **RobynHD** - Crypto market analysis with sharp, no-nonsense insights  
- **Two Minute Papers** - AI research with infectious enthusiasm for breakthroughs
- **Ivan Yakovina** - Geopolitical analysis with insider perspective

Each channel has a personalized prompt that preserves their unique voice while extracting key facts and insights.

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

**"ffmpeg not found" warning**
- This warning can be safely ignored for subtitle-only processing
- Install ffmpeg if you plan to download video files
- On Windows: `winget install ffmpeg` or download from ffmpeg.org

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