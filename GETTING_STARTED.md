# Getting Started with YouTube to Telegram

Complete setup guide from zero to running with multi-model AI summaries.

## Prerequisites

- Python 3.11 or higher
- YouTube account (for cookies)
- Telegram bot token
- LLM API key (OpenRouter recommended)

## Step 1: Installation

```bash
# Clone the repository
git clone <repository-url>
cd yt2telegram

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Basic Setup

### Configure Cookies
```bash
# Copy the template
cp COOKIES_FILE.example COOKIES_FILE

# Export your YouTube cookies using browser extension
# Save as COOKIES_FILE in project root
```

### Configure Environment
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials:
# TELEGRAM_BOT_TOKEN=your_bot_token
# TELEGRAM_CHAT_ID=your_chat_id
# LLM_PROVIDER_API_KEY=your_api_key
# MODEL=gpt-4o-mini
# BASE_URL=https://openrouter.ai/api/v1
```

## Step 3: Add Your First Channel

### Option A: Smart Setup (Recommended)
```bash
# Automatically analyze and configure any channel
python add_channel_smart.py UCbfYPyITQ-7l4upoX8nvctg
```

### Option B: Manual Configuration
```bash
# Copy example configuration
cp yt2telegram/channels/example_channel.yml yt2telegram/channels/my_channel.yml

# Edit my_channel.yml with your channel details
```

## Step 4: Test Basic Functionality

```bash
# Run once to test
python run.py
```

Look for successful processing messages in the logs.

## Step 5: Enable Multi-Model (Optional)

### Quick Multi-Model Setup
Edit your channel configuration file:

```yaml
llm_config:
  # ... existing config ...
  multi_model:
    enabled: true
    primary_model: "gpt-4o-mini"
    secondary_model: "claude-3-haiku-20240307"
    synthesis_model: "gpt-4o"
    synthesis_prompt_template_path: "yt2telegram/prompts/synthesis_template.md"
    cost_threshold_tokens: 50000
    fallback_strategy: "best_summary"
```

### Validate Multi-Model Setup
```bash
python validate_multi_model.py yt2telegram/channels/my_channel.yml
```

### Test Multi-Model
```bash
python run.py
```

Look for multi-model processing messages:
```
✅ Multi-model processing enabled for channel: MyChannel
🔄 Generating primary summary with gpt-4o-mini...
🔄 Generating secondary summary with claude-3-haiku-20240307...
🔄 Synthesizing final summary with gpt-4o...
✅ Multi-model processing completed successfully
```

## Step 6: Production Setup

### Automated Running
```bash
# Add to crontab for hourly execution
0 * * * * cd /path/to/project && python run.py >> logs/cron.log 2>&1
```

### Monitor Logs
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python run.py

# Watch for structured, color-coded output
```

## Next Steps

### Add More Channels
```bash
# Add additional channels
python add_channel_smart.py <ANOTHER_CHANNEL_ID>
```

### Enable QnA System
```bash
# Start interactive Q&A bot
python -m yt2telegram.qna.bot
```

### Optimize Configuration
- Review [MULTI_MODEL_SETUP.md](MULTI_MODEL_SETUP.md) for advanced options
- Adjust cost thresholds based on usage
- Fine-tune model combinations for your content

## Troubleshooting

### Common Issues

**"No videos found"**
- Check COOKIES_FILE is properly configured
- Verify YouTube channel ID format

**"API Error"**
- Verify API keys in .env file
- Check rate limits with your provider

**"Telegram Error"**
- Verify bot token and chat ID
- Ensure bot has message permissions

**"Multi-model not working"**
- Run validation: `python validate_multi_model.py your_config.yml`
- Check API key availability for all models

### Get Help

1. **Validation**: Always start with `python validate_multi_model.py`
2. **Documentation**: See [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)
3. **Debug Mode**: Use `LOG_LEVEL=DEBUG python run.py`
4. **Examples**: Check working configurations in `yt2telegram/channels/`

## Success Indicators

You'll know everything is working when you see:

1. **Successful channel processing** in logs
2. **Telegram messages** with video summaries
3. **Multi-model processing** messages (if enabled)
4. **No error messages** in structured logs

## What's Next?

- **Explore Features**: Try the QnA system, video tagging
- **Optimize Costs**: Adjust model combinations and thresholds
- **Scale Up**: Add more channels and fine-tune configurations
- **Monitor**: Set up proper logging and monitoring for production

Welcome to enhanced AI-powered YouTube monitoring! 🚀