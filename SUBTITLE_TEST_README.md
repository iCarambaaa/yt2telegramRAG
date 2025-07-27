# YouTube Subtitle Testing Script

This script provides comprehensive testing and extraction capabilities for YouTube video subtitles, including both manual and auto-generated subtitles.

## Features

- **Video Information Extraction**: Get detailed metadata about any YouTube video
- **Subtitle Listing**: Lists all available subtitle languages and types
- **Multiple Download Methods**: Uses both yt-dlp and YouTubeTranscriptApi
- **Verbose Logging**: Detailed logs for debugging and analysis
- **JSON Export**: Saves all results to a structured JSON file
- **Cookie Support**: Optional cookies file for age-restricted content

## Installation

Ensure you have the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
python test_subtitles.py
```

This will test the default video ID: `IE1E9m5u488`

### Custom Video ID

```bash
python test_subtitles.py YOUR_VIDEO_ID
```

Example:

```bash
python test_subtitles.py IE1E9m5u488
```

### With Cookies (for age-restricted content)

Set the `COOKIES_FILE` environment variable in your `.env` file:

```bash
COOKIES_FILE=/path/to/youtube_cookies.txt
```

Then run:

```bash
python test_subtitles.py IE1E9m5u488
```

## Output Files

- **subtitle_test.log**: Detailed verbose logging
- **subtitle*test_results*{VIDEO_ID}.json**: Structured results in JSON format

## JSON Output Structure

The results file contains:

```json
{
  "video_id": "IE1E9m5u488",
  "video_info": {
    "id": "video_id",
    "title": "Video Title",
    "uploader": "Channel Name",
    "duration": 1234,
    "upload_date": "20240101",
    "view_count": 123456,
    "description": "Video description...",
    "subtitles": {...},
    "automatic_captions": {...}
  },
  "available_subtitles": {
    "manual_subtitles": ["English (en)", "German (de)"],
    "auto_subtitles": ["English (en)", "German (de)"],
    "yt_dlp_subtitles": ["en", "de"],
    "yt_dlp_auto_captions": ["en", "de"]
  },
  "downloaded_subtitles": {
    "manual_en": {
      "method": "yt-dlp",
      "language": "en",
      "type": "manual",
      "content_length": 12345,
      "preview": "First 200 chars..."
    },
    "auto_en": {
      "method": "yt-dlp",
      "language": "en",
      "type": "auto",
      "content_length": 12345,
      "preview": "First 200 chars..."
    }
  },
  "errors": []
}
```

## Methods Used

### 1. yt-dlp

- **Manual Subtitles**: Uses `writesubtitles=True`
- **Auto-generated Subtitles**: Uses `writeautomaticsub=True`
- **Formats**: Supports VTT, SRT, and other subtitle formats

### 2. YouTubeTranscriptApi

- **Manual Transcripts**: Human-created subtitles
- **Auto-generated Transcripts**: YouTube's automatic speech recognition
- **Segmented Format**: Provides timestamped text segments

## Troubleshooting

### Common Issues

1. **No subtitles found**: Some videos don't have subtitles
2. **Age-restricted content**: Use cookies file
3. **Region restrictions**: Use appropriate VPN or cookies
4. **API limits**: YouTubeTranscriptApi has rate limits

### Debug Mode

The script runs with DEBUG level logging. Check `subtitle_test.log` for detailed information.

### Cookie File Creation

To create a cookies file:

1. Install browser extension like "Get cookies.txt"
2. Visit YouTube and log in
3. Export cookies to `youtube_cookies.txt`
4. Set `COOKIES_FILE=youtube_cookies.txt` in `.env`

## Examples

### Testing a Video with Multiple Subtitle Languages

```bash
python test_subtitles.py dQw4w9WgXcQ
```

### Testing a Video with Auto-generated Subtitles Only

```bash
python test_subtitles.py abc123xyz
```

### Testing Age-restricted Content

```bash
# First set COOKIES_FILE in .env
python test_subtitles.py restricted_video_id
```

## Integration with Main Script

This testing script uses the same libraries and patterns as the main `youtube2telegram.py` script, making it easy to integrate findings into the production pipeline.

## Performance Notes

- **Network Usage**: Downloads subtitle files temporarily
- **Storage**: Temporary files are cleaned up automatically
- **Memory**: Large subtitle files are handled efficiently
- **Rate Limiting**: Respects YouTube's rate limits
