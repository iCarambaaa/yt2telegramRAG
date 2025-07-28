# Comprehensive Q&A Bot Documentation

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Design](#architecture-design)
3. [Component Deep Dive](#component-deep-dive)
4. [Configuration Guide](#configuration-guide)
5. [Deployment Instructions](#deployment-instructions)
6. [API Reference](#api-reference)
7. [Database Schema](#database-schema)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Advanced Usage](#advanced-usage)
10. [Performance Optimization](#performance-optimization)

---

## System Overview

The Q&A Bot System is a sophisticated natural language processing system that enables users to query YouTube channel content through conversational interfaces. Built as a modular extension to the existing yt2telegramRAG system, it provides intelligent responses based on video summaries and subtitles.

### Key Capabilities

- **Natural Language Queries**: Users can ask questions in plain English
- **Contextual Search**: Searches across video summaries and full subtitles
- **Multi-Channel Support**: Handles multiple YouTube channels independently
- **Shared Chat Architecture**: Uses same chat ID as summary bot for unified experience
- **Real-time Processing**: Provides immediate responses via polling mechanism

---

## Architecture Design

### High-Level Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Telegram      │────▶│   Q&A Bot        │────▶│   Database      │
│   Interface     │     │   Application    │     │   (SQLite)      │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   OpenRouter     │
                       │   API (LLM)      │
                       └──────────────────┘
```

### Component Architecture

```
channel_manager/qna/
├── bot.py              # Telegram Bot Interface Layer
├── config.py           # Configuration Management
├── database.py         # Data Access Layer
├── handler.py          # Business Logic Layer
└── examples/           # Configuration Templates
```

---

## Component Deep Dive

### 1. Bot Layer (`bot.py`)

**Purpose**: Telegram bot interface with message handling
**Key Classes**: `QnABot`

#### Message Flow

1. **Command Processing**: `/ask`, `/search`, `/latest`, `/help`
2. **Natural Language**: Direct text messages
3. **Typing Indicators**: Real-time feedback during processing

#### Handler Registration

```python
application.add_handler(CommandHandler("start", self.start))
application.add_handler(CommandHandler("ask", self.ask))
application.add_handler(CommandHandler("search", self.search))
application.add_handler(CommandHandler("latest", self.latest))
application.add_handler(CommandHandler("help", self.help))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
```

### 2. Configuration Layer (`config.py`)

**Purpose**: Centralized configuration management
**Key Classes**: `QnAConfig`

#### Configuration Schema

```yaml
bot_token: str # Telegram bot token
channel_name: str # Display name for bot
chat_id: int # Telegram chat ID (same as summary bot)
database_path: str # Path to SQLite database
openrouter_key: str # OpenRouter API key
openrouter_model: str # AI model identifier
max_context_length: int # Context window size
max_results: int # Maximum search results
system_prompt: str # AI behavior instructions
```

### 3. Database Layer (`database.py`)

**Purpose**: Efficient data retrieval from channel databases
**Key Classes**: `DatabaseQuery`

#### Query Capabilities

- **Full-text search** across subtitles and summaries
- **Video metadata** retrieval
- **Latest content** queries
- **Relevance scoring** using TF-IDF

#### SQL Schema Requirements

```sql
-- Videos table
CREATE TABLE videos (
    id TEXT PRIMARY KEY,
    title TEXT,
    summary TEXT,
    upload_date TEXT,
    duration INTEGER
);

-- Subtitles table
CREATE TABLE subtitles (
    id INTEGER PRIMARY KEY,
    video_id TEXT,
    text TEXT,
    start_time REAL,
    FOREIGN KEY (video_id) REFERENCES videos(id)
);
```

### 4. Handler Layer (`handler.py`)

**Purpose**: Core business logic for Q&A processing
**Key Classes**: `QnAHandler`

#### Processing Pipeline

1. **Query Analysis**: Parse user intent
2. **Content Retrieval**: Search relevant videos
3. **Context Building**: Compile relevant excerpts
4. **AI Processing**: Generate intelligent response
5. **Response Formatting**: Structure final answer

---

## Configuration Guide

### Step 1: Create Bot Token

1. Message [@BotFather](https://t.me/BotFather)
2. Send `/newbot`
3. Follow prompts to create bot
4. Copy the provided token

### Step 2: Determine Chat ID

Use the same chat ID as your summary bot:

- Check your existing channel configuration
- Or use [@userinfobot](https://t.me/userinfobot) to get chat ID

### Step 3: Create Configuration File

#### Basic Configuration Template

```yaml
# bot_config.yml
bot_token: "123456789:ABCdefGHIjklMNOpqrSTUvwxyz"
channel_name: "My Channel Q&A"
chat_id: -1001234567890
database_path: "../downloads/my_channel.db"
openrouter_key: "sk-or-v1-..."
openrouter_model: "anthropic/claude-3.5-sonnet"
```

#### Advanced Configuration

```yaml
# advanced_config.yml
bot_token: "YOUR_BOT_TOKEN"
channel_name: "Advanced Q&A Bot"
chat_id: -1001234567890
database_path: "../downloads/channel.db"
openrouter_key: "YOUR_API_KEY"
openrouter_model: "anthropic/claude-3.5-sonnet"
openrouter_url: "https://openrouter.ai/api/v1/chat/completions"

# Q&A Settings
max_context_length: 4000
max_results: 5
response_timeout: 30

# AI Behavior
system_prompt: |
  You are an expert assistant for YouTube content analysis.
  Provide accurate, concise answers based on video content.
  Always cite specific video titles when referencing information.
  If information isn't available, clearly state so.
```

---

## Deployment Instructions

### Local Development

```bash
# 1. Navigate to qna directory
cd channel_manager/qna

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create configuration
cp examples/robynhd_qna.yml my_config.yml
# Edit my_config.yml with your settings

# 4. Run bot
python bot.py my_config.yml
```

### Production Deployment

#### Using systemd (Linux)

```ini
# /etc/systemd/system/qna-bot.service
[Unit]
Description=Q&A Telegram Bot
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/path/to/channel_manager/qna
ExecStart=/usr/bin/python3 bot.py /path/to/config.yml
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Using Docker

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "bot.py", "config.yml"]
```

---

## API Reference

### OpenRouter API Integration

#### Request Format

```json
POST https://openrouter.ai/api/v1/chat/completions
{
  "model": "anthropic/claude-3.5-sonnet",
  "messages": [
    {
      "role": "system",
      "content": "System prompt here"
    },
    {
      "role": "user",
      "content": "User question + context"
    }
  ],
  "max_tokens": 1000
}
```

#### Response Format

```json
{
  "choices": [
    {
      "message": {
        "content": "Generated response"
      }
    }
  ]
}
```

### Database Query API

#### Search Videos

```python
from database import DatabaseQuery

db = DatabaseQuery("path/to/database.db")
results = db.search_videos("quantum computing", limit=5)
```

#### Get Latest Videos

```python
latest = db.get_latest_videos(limit=3)
```

---

## Database Schema

### Videos Table

| Column      | Type    | Description                    |
| ----------- | ------- | ------------------------------ |
| id          | TEXT    | YouTube video ID (primary key) |
| title       | TEXT    | Video title                    |
| summary     | TEXT    | AI-generated summary           |
| upload_date | TEXT    | ISO format upload date         |
| duration    | INTEGER | Duration in seconds            |

### Subtitles Table

| Column     | Type    | Description                |
| ---------- | ------- | -------------------------- |
| id         | INTEGER | Auto-increment primary key |
| video_id   | TEXT    | Foreign key to videos      |
| text       | TEXT    | Subtitle text content      |
| start_time | REAL    | Timestamp in video         |

### Channels Table

| Column      | Type | Description         |
| ----------- | ---- | ------------------- |
| id          | TEXT | Channel ID          |
| name        | TEXT | Channel name        |
| last_update | TEXT | Last sync timestamp |

---

## Troubleshooting Guide

### Common Issues and Solutions

#### Issue: Bot Not Responding

**Symptoms**: No response to messages
**Solutions**:

1. Verify bot token is correct
2. Check bot is started via @BotFather
3. Ensure bot has message permissions
4. Check chat ID matches summary bot

#### Issue: Database Connection Errors

**Symptoms**: "Database not found" errors
**Solutions**:

1. Verify database path is correct
2. Check file permissions
3. Ensure database exists and has data
4. Test with absolute paths

#### Issue: API Rate Limits

**Symptoms**: "Rate limit exceeded" errors
**Solutions**:

1. Check OpenRouter account credits
2. Reduce `max_context_length`
3. Implement request caching
4. Add retry logic with backoff

#### Issue: Poor Response Quality

**Symptoms**: Irrelevant or vague answers
**Solutions**:

1. Improve system prompt
2. Increase `max_results`
3. Check database content quality
4. Adjust search parameters

### Debug Mode

Enable detailed logging:

```bash
export LOG_LEVEL=DEBUG
python bot.py config.yml
```

---

## Advanced Usage

### Custom System Prompts

Create specialized behavior for different channels:

#### Educational Channel

```yaml
system_prompt: |
  You are an educational assistant. Break down complex topics into simple terms.
  Use analogies and examples from the videos. Encourage further learning.
```

#### Technical Channel

```yaml
system_prompt: |
  You are a technical expert. Provide detailed, accurate explanations.
  Include specific technical details and cite exact timestamps when relevant.
```

### Multi-Bot Setup

Run multiple Q&A bots for different channels:

```bash
# Terminal 1
python bot.py configs/tech_qna.yml

# Terminal 2
python bot.py configs/science_qna.yml

# Terminal 3
python bot.py configs/history_qna.yml
```

### Custom Query Processing

Extend the handler for specialized use cases:

```python
from handler import QnAHandler

class CustomHandler(QnAHandler):
    def process_query(self, query):
        # Custom preprocessing
        processed = self.custom_preprocessing(query)

        # Use parent processing
        response = super().search_and_answer(processed)

        # Custom postprocessing
        return self.custom_formatting(response)
```

---

## Performance Optimization

### Database Optimization

```sql
-- Create indexes for faster searches
CREATE INDEX idx_subtitles_text ON subtitles(text);
CREATE INDEX idx_videos_upload_date ON videos(upload_date);
CREATE INDEX idx_subtitles_video_id ON subtitles(video_id);
```

### Memory Management

- Use connection pooling for database queries
- Implement result caching for frequent queries
- Monitor memory usage with large contexts

### Response Time Optimization

1. **Reduce context size**: Lower `max_context_length`
2. **Limit results**: Set `max_results` to 3-5
3. **Cache responses**: Store answers to common questions
4. **Async processing**: Use asyncio for concurrent operations

### Monitoring

```python
# Add performance metrics
import time

start_time = time.time()
response = handler.search_and_answer(query)
processing_time = time.time() - start_time
logger.info(f"Query processed in {processing_time:.2f}s")
```

---

## Security Best Practices

### API Key Management

```bash
# Use environment variables
export OPENROUTER_KEY="your-key-here"
export BOT_TOKEN="your-bot-token"

# In config.yml
openrouter_key: ${OPENROUTER_KEY}
bot_token: ${BOT_TOKEN}
```

### Access Control

- Restrict bot commands to specific chat IDs
- Implement rate limiting per user
- Log all queries for audit purposes

### Data Privacy

- Don't log sensitive user queries
- Implement data retention policies
- Use HTTPS for all API calls

---

## Monitoring and Maintenance

### Health Checks

```bash
# Create health check script
#!/bin/bash
curl -f http://localhost:8080/health || exit 1
```

### Log Rotation

```bash
# Configure logrotate
/var/log/qna-bot/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

### Backup Strategy

- Regular database backups
- Configuration file versioning
- API key rotation schedule

---

## Migration Guide

### From Summary Bot to Q&A Bot

1. **Shared Chat ID**: Use same chat ID as summary bot
2. **Database Path**: Point to existing channel database
3. **Bot Token**: Create new bot via @BotFather
4. **Configuration**: Copy and adapt existing channel config

### Database Migration

If upgrading from older schema:

```sql
-- Add missing columns
ALTER TABLE videos ADD COLUMN IF NOT EXISTS summary TEXT;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS duration INTEGER;
```

---

## Contributing

### Development Setup

```bash
git clone repository
cd channel_manager/qna
pip install -r requirements.txt
pip install pytest pytest-asyncio

# Run tests
pytest tests/
```

### Code Style

- Follow PEP 8 guidelines
- Use type hints
- Add docstrings to all functions
- Write unit tests for new features

---

## Support and Community

### Getting Help

1. Check this documentation
2. Review example configurations
3. Check GitHub issues
4. Join community discussions

### Reporting Issues

Include in bug reports:

- Configuration file (redact sensitive data)
- Error logs
- Steps to reproduce
- Expected vs actual behavior

---

## Version History

### v1.0.0 (Current)

- Initial Q&A bot implementation
- Multi-channel support
- OpenRouter API integration
- Shared chat architecture
- Comprehensive documentation

---

## License and Legal

This project is part of the yt2telegramRAG system. Ensure compliance with:

- YouTube Terms of Service
- Telegram Bot API Terms
- OpenRouter API Terms
- Data protection regulations (GDPR, etc.)

---

**Last Updated**: July 27, 2025  
**Documentation Version**: 1.0.0  
**System Version**: 1.0.0
