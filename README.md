# YouTube to Telegram

Automated YouTube channel monitoring with AI-powered summaries and interactive Q&A. Delivers style-preserving summaries to Telegram with RAG-powered conversations.

**Core Features:**
- Multi-model summarization with intelligent synthesis
- Channel-specific Q&A with video tagging
- Smart channel setup with automated analysis
- Subtitle cleaning (88-89% size reduction)
- Multi-language support

---

## Quick Start

### Single Video Processing
```bash
pip install -r requirements.txt
cp .env.example .env  # Add your API keys
python process_single_video.py https://www.youtube.com/watch?v=VIDEO_ID
```

### Channel Monitoring
```bash
# Setup
pip install -r requirements.txt
cp COOKIES_FILE.example COOKIES_FILE  # Export YouTube cookies using browser extension
cp .env.example .env  # Configure API keys

# Add channel (auto-analyzes and creates config)
python add_channel_smart.py UCbfYPyITQ-7l4upoX8nvctg

# Run
python run.py  # Main processing
python -m yt2telegram.qna.bot  # Optional Q&A bot
```

---



## Configuration

### Smart Channel Setup
```bash
python add_channel_smart.py <CHANNEL_ID>
```
Automatically analyzes videos, generates personalized prompts, and creates optimized configuration.

### Manual Configuration
Create YAML files in `yt2telegram/channels/`:

**Single-Model:**
```yaml
name: "Your Channel"
channel_id: "UCxxxxxxxxxxxxxxxxxx"
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

**Multi-Model:**
```yaml
name: "Your Channel"
channel_id: "UCxxxxxxxxxxxxxxxxxx"
db_path: "yt2telegram/downloads/your_channel.db"
cookies_file: "COOKIES_FILE"
max_videos_to_fetch: 3

multi_model_config:
  model_a:
    llm_api_key_env: "OPENAI_API_KEY"
    llm_model: "gpt-4o-mini"
    llm_base_url: "https://api.openai.com/v1"
    llm_prompt_template_path: "yt2telegram/prompts/your_prompt.md"
  model_b:
    llm_api_key_env: "ANTHROPIC_API_KEY"
    llm_model: "claude-3-5-haiku-20241022"
    llm_base_url: "https://api.anthropic.com"
    llm_prompt_template_path: "yt2telegram/prompts/your_prompt.md"
  synthesis_template_path: "yt2telegram/prompts/synthesis_template.md"

telegram_bots:
  - name: "Your Bot"
    token_env: "TELEGRAM_BOT_TOKEN"
    chat_id_env: "YOUR_CHANNEL_CHAT_ID"

subtitles: ["en"]
```

**Environment Variables:**
```bash
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Primary LLM Provider (OpenRouter, OpenAI, etc.)
LLM_PROVIDER_API_KEY=your_api_key
MODEL=gpt-4o-mini
BASE_URL=https://openrouter.ai/api/v1

# Multi-Model Support (Optional)
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_BASE_URL=https://api.openai.com/v1
ANTHROPIC_BASE_URL=https://api.anthropic.com
```

---





## Deployment

**Cron (hourly):**
```bash
0 * * * * cd /path/to/project && python run.py >> logs/cron.log 2>&1
```

**Systemd:**
```ini
[Unit]
Description=YouTube to Telegram
After=network.target

[Service]
Type=oneshot
WorkingDirectory=/path/to/project
ExecStart=/usr/bin/python3 run.py
User=your_user

[Install]
WantedBy=multi-user.target
```

---

## Troubleshooting

**No videos found:** Check `COOKIES_FILE` (export YouTube cookies using browser extension like "Get cookies.txt")

**LLM API errors:** Verify API key and model name in `.env`

**Telegram failures:** Verify bot token, chat ID, and bot permissions

**ffmpeg warnings:** Safe to ignore for subtitle-only processing

**Debug mode:**
```bash
export LOG_LEVEL=DEBUG
python run.py
```

---

## License

MIT License