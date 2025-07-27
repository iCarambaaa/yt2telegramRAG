# YouTube Subtitle and Metadata Downloader

A comprehensive Python script for downloading subtitles and metadata from YouTube videos using yt-dlp. This tool prioritizes original language subtitles and falls back to auto-generated subtitles when manual ones aren't available.

## Features

- ✅ Downloads subtitles in the video's original language
- ✅ Falls back to auto-generated subtitles when manual subtitles aren't available
- ✅ Downloads comprehensive video metadata
- ✅ Extracts clean text from subtitle files (removes timestamps and formatting)
- ✅ Organized file structure with separate folders for each video
- ✅ Detailed logging and error handling
- ✅ JSON summary reports for easy integration

## Installation

1. Ensure Python 3.7+ is installed
2. Install required dependencies:
   ```bash
   pip install yt-dlp
   ```

## Usage

### Basic Usage

```bash
python yt_dlp_subtitle_downloader.py [VIDEO_ID]
```

### Example

```bash
python yt_dlp_subtitle_downloader.py IE1E9m5u488
```

### Command Line Arguments

- `VIDEO_ID`: YouTube video ID (e.g., IE1E9m5u488)
- If no video ID is provided, it defaults to IE1E9m5u488

## Output Structure

The script creates an organized directory structure:

```
downloads/
└── [VIDEO_ID]/
    ├── [VIDEO_TITLE].metadata.json      # Complete video metadata
    ├── [VIDEO_TITLE].[LANGUAGE].srt     # Subtitle file (SRT format)
    ├── [VIDEO_TITLE].[LANGUAGE]_clean.txt  # Clean text without timestamps
    └── [VIDEO_ID]_summary.json          # Summary report
```

## File Descriptions

### Metadata JSON

Contains comprehensive video information including:

- Title, description, duration
- Upload date, view count
- Channel information
- Video tags and categories
- Thumbnail URLs
- Available subtitle languages

### Subtitle Files

- **.srt**: Standard subtitle format with timestamps
- **\_clean.txt**: Plain text without timestamps or formatting

### Summary Report

A concise JSON file with:

- Video ID and title
- Uploader information
- Duration and view count
- Original language
- List of downloaded subtitle files
- List of clean text files

## Language Priority

The script follows this priority order for subtitle selection:

1. **Manual subtitles** in the video's original language
2. **Auto-generated subtitles** in the video's original language
3. **Manual subtitles** in German (fallback)
4. **Auto-generated subtitles** in German (fallback)
5. **Any available subtitles** (last resort)

## Error Handling

The script includes comprehensive error handling for:

- Missing yt-dlp installation
- Network connectivity issues
- Video not found
- Subtitles not available
- File system errors

## Logging

All operations are logged to:

- Console output
- `yt_dlp_subtitle_downloader.log` file

## Integration with Existing System

This script complements the existing `extract_clean_subtitles.py` by:

- Using yt-dlp instead of YouTubeTranscriptApi
- Providing more reliable subtitle extraction
- Including metadata alongside subtitles
- Creating organized output directories

## Troubleshooting

### yt-dlp not found

```bash
pip install yt-dlp
```

### Unicode encoding issues

The script handles UTF-8 encoding for international characters. If you encounter issues, ensure your terminal supports UTF-8.

### No subtitles available

The script will inform you if no subtitles are available for the requested language and will attempt to download auto-generated subtitles instead.

## Examples

### Download subtitles for a specific video:

```bash
python yt_dlp_subtitle_downloader.py dQw4w9WgXcQ
```

### Process multiple videos:

```bash
python yt_dlp_subtitle_downloader.py VIDEO_ID_1
python yt_dlp_subtitle_downloader.py VIDEO_ID_2
```

## Advanced Usage

### Custom output directory:

Modify the `output_dir` parameter in the `YouTubeSubtitleDownloader` class initialization:

```python
downloader = YouTubeSubtitleDownloader(output_dir="my_custom_folder")
```

### Batch processing:

Create a batch script to process multiple videos:

```python
# batch_process.py
from yt_dlp_subtitle_downloader import YouTubeSubtitleDownloader

video_ids = ["IE1E9m5u488", "dQw4w9WgXcQ", "another_video_id"]
downloader = YouTubeSubtitleDownloader()

for video_id in video_ids:
    downloader.process_video(video_id)
```

## Dependencies

- Python 3.7+
- yt-dlp (automatically handles all YouTube-related dependencies)

## License

This script is provided as-is for educational and personal use. Please respect YouTube's terms of service and copyright regulations when downloading content.
