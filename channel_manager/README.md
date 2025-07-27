# Channel Manager

This directory contains the independent multi-channel management system for the YouTube to Telegram RAG application. It allows you to monitor multiple YouTube channels, process their videos, summarize content using an LLM, and send notifications to various Telegram bots/chats, all with individual configurations and scheduling.

## Features

*   **Multi-Channel Support:** Manage an arbitrary number of YouTube channels, each with its own isolated configuration.
*   **Smart Scheduling:** Define daily, weekly, or monthly processing schedules for each channel.
*   **Dedicated Databases:** Each channel uses its own SQLite database to store processed video information, ensuring data isolation.
*   **Configurable Video Fetching:** Specify how many of the latest videos to fetch from a channel's feed.
*   **Flexible Telegram Notifications:** Configure multiple Telegram bots per channel, each sending notifications to different chat IDs.
*   **Advanced Subtitle Handling:** Prioritize subtitle languages and types (manual/automatic) for download.
*   **Custom LLM Prompts:** Define unique summarization prompts for each channel to tailor the LLM's output.
*   **Robust Retry Mechanism:** Built-in retries for external API calls (YouTube, LLM, Telegram) to handle transient network issues.

## Setup

1.  **Environment Variables:**
    Create or update your project's root `.env` file with the necessary API keys and tokens. These are referenced in your channel configuration files.

    Example `.env` entries:
    ```
    LLM_PROVIDER_API_KEY="your_openai_api_key_here"
    MAIN_TELEGRAM_BOT_TOKEN="your_main_bot_token_here"
    ADMIN_TELEGRAM_BOT_TOKEN="your_admin_bot_token_here"
    # Add other bot tokens as defined in your channel configs
    ```

2.  **Install Dependencies:**
    Ensure you have all required Python packages installed. You can do this by running:
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

Channel configurations are defined in individual YAML files located in the `channel_manager/channels/` directory. You can copy the `example_channel.yml` as a template for new channels.

**`channel_manager/channels/your_channel_name.yml` example:**

```yaml
# General Channel Information
name: "Your Channel Name" # A human-readable name for the channel
channel_id: "UCsXVk37bltHxD1rDPwtNM8Q" # The actual YouTube Channel ID (e.g., from the channel's URL)
schedule: "daily" # How often to check for new videos: "daily", "weekly", "monthly"
db_path: "channel_manager/downloads/your_channel_name.db" # Path to this channel's dedicated SQLite DB
cookies_file: null # Optional: Path to a cookies.txt file for accessing private videos/channels
max_videos_to_fetch: 5 # Number of latest videos to fetch from the channel's feed (e.g., 1 for daily checks, more for initial setup or less frequent schedules)

# Retry Configuration for external API calls
retry_attempts: 3 # Number of times to retry a failed operation (e.g., API call, download)
retry_delay_seconds: 5 # Delay in seconds between retry attempts

# LLM (Large Language Model) Configuration for Summarization
llm_config:
  llm_api_key_env: "LLM_PROVIDER_API_KEY" # Environment variable name for the LLM API key
  llm_base_url: "https://api.openai.com/v1" # LLM API endpoint (e.g., for OpenAI, custom local LLMs)
  llm_model: "gpt-4o-mini" # Specific LLM model to use for summarization
  # Custom prompt template for this channel's video summaries.
  # The '{content}' placeholder will be replaced by the cleaned video subtitles.
  llm_prompt_template: "Summarize the following video content from '{name}'. Focus on key takeaways and actionable insights for a technical audience.

Content: {content}"

# Telegram Bot(s) Configuration for Notifications
# A channel can have multiple bots, each sending to a different chat_id.
telegram_bots:
  - name: "Main Channel Bot" # A descriptive name for this bot instance
    token_env: "MAIN_TELEGRAM_BOT_TOKEN" # Environment variable name for this bot's token
    chat_id: "-1001234567890" # The Telegram chat ID where notifications will be sent (can be a user, group, or channel ID)
  - name: "Admin Alerts Bot" # Another bot for administrative alerts, for example
    token_env: "ADMIN_TELEGRAM_BOT_TOKEN" # Environment variable name for the admin bot's token
    chat_id: "987654321" # Admin's personal chat ID

# Subtitle Preferences
# The order matters: the system will try to download subtitles in this order
# until a match is found.
subtitles:
  - lang: "en" # Language code (e.g., "en", "de", "fr")
    type: "manual" # "manual" (human-generated) or "automatic" (YouTube's auto-generated)
  - lang: "de"
    type: "manual"
  - lang: "en"
    type: "automatic"
```

## Running the Channel Manager

To run the multi-channel manager, execute the `main.py` script from the project root:

```bash
python -m channel_manager.main
```

It is recommended to set up a cron job (or a scheduled task on Windows) to run this command periodically (e.g., once every 24 hours). The manager will automatically determine which channels are due for processing based on their configured schedules.

## Directory Structure

```
channel_manager/
├── __init__.py             # Python package initializer
├── main.py                 # Main entry point and orchestrator
├── glob.py                 # Utility to find channel configuration files
├── database.py             # Handles SQLite database operations for channels and videos
├── youtube_client.py       # Interacts with YouTube (via yt-dlp) to fetch video metadata
├── youtube_dlp.py          # Handles downloading raw subtitles
├── subtitle_cleaner.py     # Cleans raw subtitle content
├── llm_summarizer.py       # Generates video summaries using an LLM
├── telegram_bot.py         # Sends notifications to Telegram
├── channels/               # Directory for individual channel configuration YAML files
│   └── example_channel.yml # Example channel configuration
└── downloads/              # Directory for channel-specific data (e.g., raw subtitles, DBs)
    └── <channel_id>/
        └── raw_subtitles/
```
