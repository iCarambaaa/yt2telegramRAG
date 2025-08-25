# Deployment Guide

Complete guide for deploying the YouTube to Telegram Channel Manager in production.

## 🚀 Quick Production Setup

### 1. Server Requirements
- **OS**: Linux (Ubuntu 20.04+ recommended)
- **Python**: 3.8+
- **Memory**: 512MB minimum, 1GB recommended
- **Storage**: 2GB for databases and logs
- **Network**: Stable internet connection

### 2. Installation
```bash
# Clone repository
git clone <your-repo-url>
cd yt2telegram

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit with your credentials
nano .env
```

**Required Environment Variables:**
```bash
# Telegram Bot
TELEGRAM_BOT_TOKEN="your_bot_token_here"

# Channel-specific chat IDs
TWOMINUTEPAPERS_CHAT_ID="your_chat_id"
DAVID_ONDREJ_CHAT_ID="your_chat_id"
ISAAC_ARTHUR_CHAT_ID="your_chat_id"
IVAN_YAKOVINA_CHAT_ID="your_chat_id"
ROBYNHD_CHAT_ID="your_chat_id"

# Primary LLM Provider (OpenRouter recommended)
LLM_PROVIDER_API_KEY="your_openrouter_api_key"
MODEL="gpt-4o-mini"
BASE_URL="https://openrouter.ai/api/v1"

# Optional: Additional providers for multi-model
ANTHROPIC_API_KEY="your_anthropic_key"
ANTHROPIC_BASE_URL="https://api.anthropic.com"
OPENAI_API_KEY="your_openai_key"
OPENAI_BASE_URL="https://api.openai.com/v1"
```

### 4. YouTube Cookies Setup
```bash
# Copy cookies template
cp COOKIES_FILE.example COOKIES_FILE

# Add your YouTube session cookies
# Use browser extension to export cookies in Netscape format
```

### 5. Test Run
```bash
# Test with single channel
python run.py

# Test QnA system (optional)
python -m yt2telegram.qna.bot

# Check logs for any issues
tail -f logs/app.log
```

## 🔄 Automated Scheduling

### Option 1: Cron (Recommended)
```bash
# Edit crontab
crontab -e

# Add entry to run every hour
0 * * * * cd /path/to/yt2telegram && /path/to/venv/bin/python run.py >> logs/cron.log 2>&1

# Or every 30 minutes for more frequent updates
*/30 * * * * cd /path/to/yt2telegram && /path/to/venv/bin/python run.py >> logs/cron.log 2>&1
```

### Option 2: Systemd Timer
```bash
# Create service file
sudo nano /etc/systemd/system/yt2telegram.service
```

```ini
[Unit]
Description=YouTube to Telegram Channel Manager
After=network.target

[Service]
Type=oneshot
User=your_user
WorkingDirectory=/path/to/yt2telegram
Environment=PATH=/path/to/venv/bin
ExecStart=/path/to/venv/bin/python run.py
StandardOutput=append:/path/to/yt2telegram/logs/systemd.log
StandardError=append:/path/to/yt2telegram/logs/systemd.log
```

```bash
# Create timer file
sudo nano /etc/systemd/system/yt2telegram.timer
```

```ini
[Unit]
Description=Run YouTube to Telegram every hour
Requires=yt2telegram.service

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
# Enable and start
sudo systemctl enable yt2telegram.timer
sudo systemctl start yt2telegram.timer

# Check status
sudo systemctl status yt2telegram.timer
```

## 🐳 Docker Deployment

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p logs

# Run as non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "run.py"]
```

### Docker Compose
```yaml
version: '3.8'

services:
  yt2telegram:
    build: .
    container_name: yt2telegram
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs
      - ./yt2telegram/downloads:/app/yt2telegram/downloads
      - ./.env:/app/.env
      - ./COOKIES_FILE:/app/COOKIES_FILE
    environment:
      - TZ=UTC
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # Optional: Add cron container for scheduling
  cron:
    image: alpine:latest
    container_name: yt2telegram-cron
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    command: >
      sh -c "
        apk add --no-cache docker-cli &&
        echo '0 * * * * docker exec yt2telegram python run.py' | crontab - &&
        crond -f
      "
```

### Deploy with Docker
```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f yt2telegram

# Update
docker-compose pull && docker-compose up -d
```

## 📊 Monitoring & Logging

### Log Files
```bash
# Application logs
tail -f logs/app.log

# Cron logs (if using cron)
tail -f logs/cron.log

# Error logs
grep ERROR logs/app.log
```

### Health Checks
```bash
# Check last successful run
ls -la yt2telegram/downloads/*.db

# Check database contents
sqlite3 yt2telegram/downloads/twominutepapers.db "SELECT COUNT(*) FROM videos;"

# Check recent processing
sqlite3 yt2telegram/downloads/twominutepapers.db "SELECT title, processed_at FROM videos ORDER BY processed_at DESC LIMIT 5;"
```

### Monitoring Script
```bash
#!/bin/bash
# monitor.sh - Check system health

echo "=== YouTube to Telegram Health Check ==="
echo "Date: $(date)"
echo

# Check if processes are running
if pgrep -f "python.*run.py" > /dev/null; then
    echo "✅ Process is running"
else
    echo "❌ Process is not running"
fi

# Check recent database activity
for db in yt2telegram/downloads/*.db; do
    if [ -f "$db" ]; then
        channel=$(basename "$db" .db)
        last_update=$(sqlite3 "$db" "SELECT MAX(processed_at) FROM videos;" 2>/dev/null)
        echo "📺 $channel: Last update $last_update"
    fi
done

# Check log file size
log_size=$(du -h logs/app.log 2>/dev/null | cut -f1)
echo "📝 Log file size: $log_size"

# Check disk space
disk_usage=$(df -h . | tail -1 | awk '{print $5}')
echo "💾 Disk usage: $disk_usage"
```

## 🔧 Maintenance

### Regular Tasks
```bash
# Rotate logs (weekly)
mv logs/app.log logs/app.log.$(date +%Y%m%d)
touch logs/app.log

# Clean old logs (monthly)
find logs/ -name "*.log.*" -mtime +30 -delete

# Backup databases (daily)
tar -czf backups/databases-$(date +%Y%m%d).tar.gz yt2telegram/downloads/*.db

# Update dependencies (monthly)
pip install --upgrade -r requirements.txt
```

### Troubleshooting
```bash
# Check configuration
python -c "from yt2telegram.main import *; print('Config OK')"

# Test Telegram connection
python -c "
import os
from yt2telegram.services.telegram_service import TelegramService
config = {'telegram_bots': [{'name': 'Test', 'token_env': 'TELEGRAM_BOT_TOKEN', 'chat_id_env': 'TWOMINUTEPAPERS_CHAT_ID'}]}
service = TelegramService(config)
print('Telegram OK')
"

# Test LLM connection
python -c "
from yt2telegram.services.llm_service import LLMService
config = {'llm_api_key_env': 'LLM_PROVIDER_API_KEY', 'llm_model': 'gpt-4o-mini', 'llm_base_url': 'https://openrouter.ai/api/v1', 'llm_prompt_template': 'Test: {content}'}
service = LLMService(config)
print('LLM OK')
"
```

## 🔒 Security

### File Permissions
```bash
# Secure sensitive files
chmod 600 .env COOKIES_FILE
chmod 700 logs/
chmod 755 yt2telegram/downloads/
```

### Environment Security
```bash
# Use environment variables, not hardcoded values
# Rotate API keys regularly
# Keep cookies file updated
# Monitor for unauthorized access
```

### Backup Strategy
```bash
# Daily database backup
# Weekly full backup
# Monthly offsite backup
# Test restore procedures
```

## 🤖 Multi-Model Configuration

### Model Selection Strategy
```yaml
# High-quality setup (recommended for important channels)
multi_model_config:
  enabled: true
  primary_model:
    model_name: "gpt-4o-mini"      # Fast, reliable
  secondary_model:
    model_name: "claude-3-haiku"   # Different perspective
  synthesis_model:
    model_name: "gpt-4o"           # Premium quality

# Cost-optimized setup
multi_model_config:
  enabled: true
  primary_model:
    model_name: "gpt-3.5-turbo"    # Cheapest
  secondary_model:
    model_name: "gpt-4o-mini"      # Good quality/cost ratio
  synthesis_model:
    model_name: "gpt-4o-mini"      # Same as secondary
```

### Provider Configuration
```bash
# Environment variables for multiple providers
LLM_PROVIDER_API_KEY="sk-or-v1-..."           # OpenRouter
ANTHROPIC_API_KEY="sk-ant-api03-..."          # Anthropic
OPENAI_API_KEY="sk-proj-..."                  # OpenAI

BASE_URL="https://openrouter.ai/api/v1"
ANTHROPIC_BASE_URL="https://api.anthropic.com"
OPENAI_BASE_URL="https://api.openai.com/v1"
```

### Monitoring Multi-Model Usage
```bash
# Check token usage across models
grep "token_usage" logs/app.log | tail -10

# Monitor costs by provider
grep "estimated_cost" logs/app.log | tail -10

# Check fallback frequency
grep "fallback" logs/app.log | tail -10
```

## 📈 Scaling

### Multiple Servers
- Deploy on multiple servers for redundancy
- Use shared storage for databases
- Implement load balancing for API calls
- Monitor resource usage

### Performance Optimization
- Adjust `max_videos_to_fetch` based on channel activity
- Use faster LLM models for high-volume channels
- Configure multi-model strategically (faster models for summaries, premium for synthesis)
- Implement caching for repeated requests
- Monitor API rate limits across multiple providers

### Cost Optimization
- Use cheaper LLM models for less critical channels
- Configure multi-model with cost-effective model combinations
- Implement smart scheduling based on channel activity
- Monitor token usage across all model calls
- Use fallback strategies to avoid unnecessary API calls
- Optimize prompts for token efficiency

---

## 🆘 Support

### Common Issues
1. **Cookies expired** - Re-export from browser
2. **API rate limits** - Implement delays and retries
3. **Disk space** - Clean old logs and databases
4. **Memory issues** - Restart service, check for leaks

### Getting Help
- Check logs first: `tail -f logs/app.log`
- Review configuration: Ensure all environment variables are set
- Test components individually: Use troubleshooting scripts
- Monitor resource usage: CPU, memory, disk, network

### Performance Monitoring
- Track processing times
- Monitor API costs
- Check delivery success rates
- Review error patterns