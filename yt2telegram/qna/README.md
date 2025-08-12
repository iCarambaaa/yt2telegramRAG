# Q&A Bot System for YouTube Channel Summaries

This directory contains a self-contained Q&A bot system that allows users to ask questions about YouTube channel content using natural language. The bot integrates with existing channel databases and provides intelligent responses using OpenRouter's AI models.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Create Your Q&A Bot

1. Create a new bot via [@BotFather](https://t.me/BotFather)
2. Copy the bot token
3. Use the same chat ID as your existing summary bot

### 3. Configure Your Bot

Copy one of the example configurations and customize:

```bash
cp examples/robynhd_qna.yml my_channel_qna.yml
# Edit my_channel_qna.yml with your settings
```

### 4. Run the Bot

```bash
python bot.py my_channel_qna.yml
```

## 📁 Directory Structure

```
qna/
├── bot.py              # Main bot application
├── config.py           # Configuration management
├── database.py         # Database query engine
├── handler.py          # Q&A processing logic
├── requirements.txt    # Python dependencies
├── examples/           # Configuration examples
│   ├── robynhd_qna.yml
│   └── isaac_arthur_qna.yml
└── README.md          # This file
```

## 🔧 Configuration

### Required Settings

- `bot_token`: Your Telegram bot token from @BotFather
- `chat_id`: Same chat ID as your summary bot
- `database_path`: Path to your channel's SQLite database
- `openrouter_key`: Your OpenRouter API key

### Optional Settings

- `openrouter_model`: AI model to use (default: anthropic/claude-3.5-sonnet)
- `max_context_length`: Maximum characters in context (default: 4000)
- `max_results`: Maximum videos to search (default: 5)
- `system_prompt`: Custom AI behavior instructions

## 🤖 Bot Commands

### Available Commands

- `/start` - Welcome message and help
- `/ask <question>` - Ask about any video content
- `/search <keywords>` - Search video summaries
- `/latest` - Get latest video summaries
- `/help` - Show detailed help

### Natural Language

You can also send messages without commands - the bot will automatically treat them as questions.

## 💡 Usage Examples

### Ask Specific Questions

```
/ask What does the latest video say about quantum computing?
/ask How does Isaac Arthur explain the Fermi Paradox?
```

### Search by Keywords

```
/search space exploration
/search artificial intelligence future
```

### Get Latest Content

```
/latest
```

## 🔍 How It Works

1. **Database Query**: Searches video summaries and subtitles for relevant content
2. **Context Building**: Selects the most relevant videos based on your query
3. **AI Processing**: Uses OpenRouter's API to generate intelligent responses
4. **Response Formatting**: Returns concise, informative answers with video references

## 🛠️ Multi-Channel Support

The system supports multiple channels with separate configurations:

- Each channel has its own bot token
- All bots can share the same chat ID
- Each uses its own database file
- Independent configuration for each channel

## 📊 Database Schema

The bot expects the following tables in your database:

- `videos`: Video metadata and summaries
- `subtitles`: Video subtitle content
- `channels`: Channel information

## 🚨 Troubleshooting

### Common Issues

**Bot not responding**

- Check bot token is correct
- Verify chat ID matches your summary bot
- Ensure bot has permission to read messages

**No search results**

- Verify database path is correct
- Check if videos have been processed
- Ensure subtitles are available

**API errors**

- Verify OpenRouter API key
- Check API rate limits
- Ensure sufficient credits

### Debug Mode

Enable debug logging by setting environment variable:

```bash
export LOG_LEVEL=DEBUG
python bot.py my_channel_qna.yml
```

## 🔐 Security Notes

- Never commit API keys or bot tokens to version control
- Use environment variables for sensitive data
- Regularly rotate API keys
- Monitor bot usage and API costs

## 📈 Performance Tips

- Keep `max_context_length` reasonable (2000-4000 chars)
- Limit `max_results` to 3-5 videos for faster responses
- Use specific keywords for better search results
- Consider caching frequent queries

## 🔄 Integration with Summary Bot

This Q&A system is designed to work alongside your existing summary bot:

- Shares the same chat ID
- Uses the same database
- Provides complementary functionality
- Can be deployed independently

## 📞 Support

For issues or questions:

1. Check the troubleshooting section above
2. Review the example configurations
3. Ensure all dependencies are installed
4. Verify your configuration file syntax

## 📝 License

This project is part of the yt2telegramRAG system. Use responsibly and in accordance with YouTube's terms of service.
