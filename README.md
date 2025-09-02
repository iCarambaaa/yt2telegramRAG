# YouTube to Telegram

Advanced automated content monitoring and summarization system that monitors YouTube channels, generates enhanced AI-powered summaries using multi-model approach, and provides interactive QnA with channel-specific RAG conversations.

**Key Features:**
- ✅ **Multi-Model Summarization** - Enhanced quality through dual-model approach with intelligent synthesis
- ✅ **Channel-Specific QnA** - RAG-powered conversations with individual channel databases
- ✅ **Smart Channel Setup** - Automated channel analysis and configuration
- ✅ **Style-Preserving Summaries** - Maintains each creator's unique voice and perspective  
- ✅ **Smart Message Splitting** - Preserves all content across multiple messages when needed
- ✅ **Video Tagging System** - Tag specific videos for targeted questioning with full context
- ✅ **Robust Error Handling** - HTML escaping, Markdown parsing fixes, and fallback mechanisms
- ✅ **Optimized Processing** - Advanced subtitle cleaning with 88-89% size reduction
- ✅ **Multi-Language Support** - Perfect support for English, German, Russian, and more
- ✅ **Production Ready** - Comprehensive logging, retry logic, and graceful failure recovery

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
# Main processing (monitors channels and generates summaries)
python run.py

# Interactive QnA bot (optional)
python -m yt2telegram.qna.bot
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
│   ├── llm_service.py     # Single-model AI summarization
│   └── multi_model_llm_service.py # Multi-model enhanced summarization
├── utils/                 # Helper functions
│   ├── subtitle_cleaner.py
│   ├── validators.py
│   └── logging_config.py
├── channels/              # Channel configurations
│   ├── example_channel.yml    # Template (skipped in production)
│   ├── example_multi_model.yml # Multi-model template (skipped in production)
│   └── your_channels.yml      # Your actual channel configs
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

**Note:** Example configuration files (`example_channel.yml` and `example_multi_model.yml`) are automatically skipped during production runs and serve only as templates.

### Manual Channel Configuration
You can also create YAML files manually in `yt2telegram/channels/`:

#### Single-Model Configuration
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

#### Multi-Model Configuration (Enhanced Quality)
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

### Environment Variables (.env)
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

### 🧠 **Advanced AI Summaries**
- **Multi-model enhancement** - Dual-model approach with intelligent synthesis for superior quality
- **Comprehensive extraction** - 2000 tokens for detailed, complete summaries
- **Style preservation** - Maintains each creator's unique voice, humor, and perspective
- **Smart prompting** - Tailored prompts for different content types (tech, crypto, geopolitics, science)
- **No information loss** - Extracts ALL valuable information while preserving storytelling approach
- **Quality synthesis** - Combines strengths of different models for optimal results

### 📱 **Smart Telegram Delivery**
- **Multi-part messages** - Automatically splits long summaries into Part 1/2 format
- **Zero truncation** - Preserves all content instead of cutting it off
- **Robust formatting** - Markdown → HTML → Plain text fallback system
- **Emoji-rich structure** - Uses 🎯 📋 🔸 💡 ⚙️ emojis for visual appeal and easy scanning
- **Clean conversion** - Converts **bold** and `code` markdown to proper HTML tags
- **Natural boundaries** - Splits at paragraphs and sentences, not mid-word

### 🧹 **Optimized Subtitle Processing**
- **Smart deduplication** - Removes overlapping VTT subtitle segments
- **88-89% size reduction** - Dramatically reduces processing costs and improves quality
- **Multi-language support** - Perfect handling of English, German, Russian, and more
- **Content preservation** - Maintains all important information while removing redundancy

### 🚀 **Smart Channel Setup**
- **Automated analysis** - Detects content themes, style, and tone automatically
- **Personalized prompts** - Generates tailored extraction prompts for each creator
- **Clean naming** - Uses actual channel names (twominutepapers.db, david_ondrej.db)
- **Original language detection** - Uses appropriate captions automatically

### ⚡ **Production-Ready Architecture**
- **Sequential processing** - No async complexity, easier to debug and maintain
- **Comprehensive error handling** - Retry logic, graceful failures, detailed logging
- **Token optimization** - 2000 tokens balanced for quality vs cost
- **Clean structure** - Separated concerns (models, services, utils) for easy maintenance

### 🌍 **Multi-Channel & Multi-Language**
- **Unlimited channels** - Monitor any number of YouTube channels simultaneously
- **Individual configurations** - Separate prompts and databases per channel
- **Language flexibility** - Automatic original language caption detection and processing
- **Isolated pipelines** - Each channel processes independently for reliability

### 💬 **Interactive QnA System**
- **Channel-specific conversations** - RAG-powered Q&A with individual channel knowledge bases
- **Video tagging system** - Tag specific videos for targeted questioning with full context
- **Semantic search** - Find relevant content across all videos in a channel
- **Context-aware responses** - Answers based on actual video content and summaries
- **Multi-channel support** - Separate conversation contexts for each monitored channel

---

## Recent Improvements (v2.0)

### 🎯 **Smart Message Splitting**
Long summaries are now automatically split into multiple messages with clear part numbering:
```
📺 New Video from TwoMinutePapers - Part 1/2

ChatGPT 5 explained in 7 minutes

📝 Summary:
[First part of comprehensive summary...]
```
```
📺 New Video from TwoMinutePapers - Part 2/2

📝 Summary:
[Rest of comprehensive summary...]

🔗 Watch Video
```

### 🛡️ **Robust Error Handling**
- **HTML escaping** - Prevents parsing errors from content like "$10m", "<comparison>", etc.
- **Markdown fixes** - Automatically repairs malformed bold/italic markers
- **Fallback system** - Markdown → HTML → Plain text ensures delivery
- **Smart boundaries** - Splits at natural paragraph/sentence breaks

### ⚡ **Performance Optimizations**
- **Advanced subtitle cleaning** - 88-89% size reduction with smart deduplication
- **Token optimization** - 2000 tokens for comprehensive summaries
- **Efficient processing** - Reduced API costs while improving quality
- **Clean naming** - Shorter, clearer database and file names

### 📊 **Quality Improvements**
- **Comprehensive prompts** - Extract ALL valuable information
- **Style preservation** - Better maintenance of creator's unique voice
- **Multi-language excellence** - Perfect support across languages
- **Zero information loss** - Complete summaries instead of truncation

---

## Example Channels

The project includes several pre-configured channels that demonstrate different content types and styles:

- **TwoMinutePapers** (`twominutepapers.yml`) - AI research with Károly's infectious enthusiasm for breakthroughs
- **David Ondrej** (`david_ondrej.yml`) - Tech tutorials with raw, documentary-like presentation style
- **Isaac Arthur** (`isaac_arthur.yml`) - Space technology and megastructures with grand cosmic storytelling
- **RobynHD** (`robynhd_channel.yml`) - Crypto market analysis with sharp, no-nonsense insights  
- **Ivan Yakovina** (`ivan_yakovina.yml`) - Geopolitical analysis with insider perspective (Russian)

Each channel has a comprehensive, personalized prompt that:
- Extracts ALL valuable information (technical details, metrics, insights)
- Preserves the creator's unique voice and style
- Uses emoji-rich formatting (🎯 **headers**, 📊 **metrics**, 💻 `code`) for visual appeal
- Converts simple markdown to clean HTML automatically
- Processes the entire transcript thoroughly

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
- Verify bot token and chat ID in `.env`
- Check if bot is added to the chat/group
- Ensure bot has send message permissions
- Look for HTML parsing errors in logs (now automatically fixed)

**"Message truncated" or "Part 1/2 not working"**
- This is normal for very long summaries (>3800 characters)
- The system automatically splits messages to preserve all content
- Check logs to see if all parts were sent successfully

**"HTML parsing errors" (e.g., "Unsupported start tag")**
- Now automatically fixed with HTML escaping
- Content like "$10m", "<comparison>", etc. is safely handled
- System falls back to Markdown/Plain text if HTML fails

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

### Structured Logging
The system now features enhanced structured logging with semantic color coding:

- **Channel names**: Red (easy identification)
- **Video titles**: Green (content highlighting)  
- **Success counts**: Green (positive metrics)
- **Failed counts**: Red (negative metrics)
- **Errors**: Bright red (problem indication)
- **General counts**: Yellow (neutral metrics)

Example log output:
```
[02:15:30] INFO Processing channel [channel_name=Two Minute Papers, video_count=5]
[02:15:31] INFO Processing video [video_title=Amazing AI Research, video_id=abc123]
[02:15:35] INFO Processing complete [successful_count=4, failed_count=1]
```

The structured logging makes it easy to visually scan logs and quickly identify:
- Which channels are being processed
- Video processing status
- Success/failure metrics
- Any errors or issues

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