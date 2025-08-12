# Ubuntu Production Deployment Guide

## Prerequisites

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11+
sudo apt install python3.11 python3.11-pip python3.11-venv -y

# Install git
sudo apt install git -y
```

## Deployment Steps

### 1. Clone Repository
```bash
cd /opt
sudo git clone https://github.com/yourusername/yt2telegramRAG.git
sudo chown -R $USER:$USER yt2telegramRAG
cd yt2telegramRAG
```

### 2. Setup Virtual Environment
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit with your credentials
nano .env

# Setup cookies (export from browser)
nano COOKIES_FILE
```

### 4. Test Run
```bash
python run.py
```

### 5. Setup Cron Job
```bash
# Edit crontab
crontab -e

# Add this line for hourly execution:
0 * * * * cd /opt/yt2telegramRAG && /opt/yt2telegramRAG/.venv/bin/python run.py >> /var/log/yt2telegram.log 2>&1

# Or for daily at 8 AM:
0 8 * * * cd /opt/yt2telegramRAG && /opt/yt2telegramRAG/.venv/bin/python run.py >> /var/log/yt2telegram.log 2>&1
```

### 6. Setup Logging
```bash
# Create log file
sudo touch /var/log/yt2telegram.log
sudo chown $USER:$USER /var/log/yt2telegram.log

# Setup log rotation
sudo nano /etc/logrotate.d/yt2telegram
```

Add to logrotate config:
```
/var/log/yt2telegram.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 username username
}
```

## Monitoring

```bash
# Check logs
tail -f /var/log/yt2telegram.log

# Check cron status
systemctl status cron

# List cron jobs
crontab -l
```

## Troubleshooting

```bash
# Test manually
cd /opt/yt2telegramRAG
source .venv/bin/activate
python run.py

# Check permissions
ls -la COOKIES_FILE
ls -la .env

# Update code
git pull
pip install -r requirements.txt
```