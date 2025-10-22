#!/usr/bin/env python3
"""Analyze log files from YouTube to Telegram runs

Usage:
    python analyze_log.py                    # Analyze latest log file
    python analyze_log.py <log_file_path>    # Analyze specific log file
    python analyze_log.py --all              # Analyze all log files
    python analyze_log.py --list             # List all available log files
"""

import re
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime


def find_latest_log():
    """Find the most recent log file in the logs directory"""
    log_dir = Path('logs')
    if not log_dir.exists():
        print("❌ Error: logs directory not found")
        sys.exit(1)
    
    log_files = list(log_dir.glob('run_*.log'))
    if not log_files:
        print("❌ Error: No log files found in logs directory")
        sys.exit(1)
    
    # Sort by modification time, most recent first
    latest = max(log_files, key=lambda p: p.stat().st_mtime)
    return latest


def get_all_logs():
    """Get all log files sorted by date (newest first)"""
    log_dir = Path('logs')
    if not log_dir.exists():
        return []
    
    log_files = list(log_dir.glob('run_*.log'))
    return sorted(log_files, key=lambda p: p.stat().st_mtime, reverse=True)


def list_logs():
    """List all available log files"""
    log_files = get_all_logs()
    if not log_files:
        print("❌ No log files found")
        return
    
    print("=" * 80)
    print(f"AVAILABLE LOG FILES ({len(log_files)} total)")
    print("=" * 80)
    
    for i, log_file in enumerate(log_files, 1):
        file_size = log_file.stat().st_size
        mod_time = datetime.fromtimestamp(log_file.stat().st_mtime)
        
        # Extract timestamp from filename
        filename = log_file.name
        if match := re.search(r'run_(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})\.log', filename):
            timestamp = match.group(1).replace('_', ' at ')
        else:
            timestamp = "Unknown"
        
        marker = "LATEST" if i == 1 else f"   #{i}"
        print(f"{marker} {log_file.name}")
        print(f"      Run: {timestamp}")
        print(f"      Size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
        print(f"      Modified: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()


def analyze_log(log_path):
    """Analyze a single log file and return content"""
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Detect log type
        is_single_video = 'Starting single video processing' in content
        is_channel_monitoring = 'Processing channel' in content
        
        if is_single_video:
            print("[SINGLE VIDEO] Log Type: Single Video Processing")
        elif is_channel_monitoring:
            print("[CHANNEL] Log Type: Channel Monitoring")
        else:
            print("[UNKNOWN] Log Type: Unknown")
        print()
        
        return content
    except Exception as e:
        print(f"[ERROR] Error reading log file: {e}")
        sys.exit(1)


def print_analysis(content, log_path):
    """Print comprehensive analysis of log content"""
    # Set UTF-8 encoding for Windows console
    import sys
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass
    
    print("=" * 80)
    print("COMPREHENSIVE LOG ANALYSIS")
    print("=" * 80)
    print(f"Log File: {log_path}")
    
    # Extract timestamp from filename
    filename = Path(log_path).name
    if match := re.search(r'run_(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})\.log', filename):
        timestamp = match.group(1).replace('_', ' at ')
        print(f"Run Time: {timestamp}")
    
    # Get file size
    file_size = Path(log_path).stat().st_size
    print(f"File Size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
    print()

    # Detect log type
    is_single_video = 'Starting single video processing' in content
    is_channel_monitoring = 'Processing channel' in content
    
    # Initialize variables that might be used later
    videos_processed = 0
    
    if is_single_video:
        # Single video processing analysis
        print("SINGLE VIDEO PROCESSING ANALYSIS")
        print("-" * 80)
        
        # Extract video details
        video_id_match = re.search(r'Processing video \[video_id=([^,]+)', content)
        video_id = video_id_match.group(1) if video_id_match else "Unknown"
        
        title_match = re.search(r'title=([^,\]]+?)(?:,|\])', content)
        title = title_match.group(1).strip() if title_match else "Unknown"
        
        channel_match = re.search(r'channel_id=([^,\]]+)', content)
        channel_id = channel_match.group(1) if channel_match else "Unknown"
        
        lang_match = re.search(r'original_language=(\w+)', content)
        language = lang_match.group(1) if lang_match else "Unknown"
        
        print(f"Video ID: {video_id}")
        print(f"Title: {title}")
        print(f"Channel ID: {channel_id}")
        print(f"Language: {language}")
        print()
        
        # Subtitle processing
        raw_size_match = re.search(r'raw_size=(\d+)', content)
        cleaned_size_match = re.search(r'cleaned_size=(\d+)', content)
        compression_match = re.search(r'compression_ratio=([\d.]+)%', content)
        
        if raw_size_match and cleaned_size_match:
            raw_size = int(raw_size_match.group(1))
            cleaned_size = int(cleaned_size_match.group(1))
            compression = compression_match.group(1) if compression_match else "N/A"
            print(f"Subtitle Processing:")
            print(f"  Raw size: {raw_size:,} bytes ({raw_size/1024:.1f} KB)")
            print(f"  Cleaned size: {cleaned_size:,} bytes ({cleaned_size/1024:.1f} KB)")
            print(f"  Compression: {compression}%")
            print()
        
        # Summary generation
        summary_match = re.search(r'summary_length=(\d+)', content)
        if summary_match:
            summary_length = int(summary_match.group(1))
            print(f"Summary: {summary_length:,} characters")
            print()
        
        # Model information
        if 'Multi-model processing enabled' in content:
            primary_match = re.search(r'primary_model=([^,\]]+)', content)
            secondary_match = re.search(r'secondary_model=([^,\]]+)', content)
            synthesis_match = re.search(r'synthesis_model=([^,\]]+)', content)
            
            print("Model Configuration: Multi-model")
            if primary_match:
                print(f"  Primary: {primary_match.group(1)}")
            if secondary_match:
                print(f"  Secondary: {secondary_match.group(1)}")
            if synthesis_match:
                print(f"  Synthesis: {synthesis_match.group(1)}")
            print()
        elif 'Single-model processing enabled' in content:
            model_match = re.search(r'model=([^,\]]+)', content)
            if model_match:
                print(f"Model Configuration: Single-model ({model_match.group(1)})")
                print()
        
        # Processing time and cost
        proc_time_match = re.search(r'processing_time_seconds=([\d.]+)', content)
        cost_match = re.search(r'cost_estimate=([\d.]+)', content)
        
        if proc_time_match or cost_match:
            print("Performance Metrics:")
            if proc_time_match:
                proc_time = float(proc_time_match.group(1))
                print(f"  Processing time: {proc_time:.1f}s ({proc_time/60:.1f} min)")
            if cost_match:
                cost = float(cost_match.group(1))
                print(f"  Estimated cost: ${cost:.4f}")
            print()
        
        # Status
        if 'Video processing completed successfully' in content:
            print("Status: [SUCCESS] Video processed and sent to Telegram")
        elif 'Video processing failed' in content:
            print("Status: [FAILED] Video processing failed")
            # Extract error if available
            error_match = re.search(r'ERROR.*', content)
            if error_match:
                print(f"  Error: {error_match.group(0)[:100]}")
        print()
        
    elif is_channel_monitoring:
        # Channel monitoring analysis (existing code)
        print("CHANNEL MONITORING ANALYSIS")
        print("-" * 80)
        total_channels = len(re.findall(r'Processing channel \[channel_name=([^,]+)', content))
        videos_processed = len(re.findall(r'Successfully processed and sent video', content))
        videos_skipped = len(re.findall(r'Video already processed, skipping', content))
        members_only = len(re.findall(r'members-only', content))
        single_model_init = len(re.findall(r'Initializing single-model LLM service', content))
        multi_model_init = len(re.findall(r'Initializing multi-model LLM service', content))
        multi_model_complete = len(re.findall(r'Multi-model summarization completed', content))

        print(f"Total channels processed: {total_channels}")
        print(f"Videos successfully processed: {videos_processed}")
        print(f"Videos skipped (already processed): {videos_skipped}")
        print(f"Members-only videos detected: {members_only}")
        print(f"Single-model initializations: {single_model_init}")
        print(f"Multi-model initializations: {multi_model_init}")
        print(f"Multi-model completions: {multi_model_complete}")
        print()
    else:
        # Unknown log type
        print("OVERALL STATISTICS")
        print("-" * 80)
        print("Unable to determine log type - may be incomplete or corrupted")
        print()

    # Per-channel breakdown (only for channel monitoring logs)
    if is_channel_monitoring:
        print("PER-CHANNEL BREAKDOWN")
        print("-" * 80)

        channel_pattern = r'Finished processing channel \[channel_name=([^,]+), processed_count=(\d+), successful_notifications=(\d+), failed_notifications=(\d+)\]'
        channels = re.findall(channel_pattern, content)

        for channel_name, processed, successful, failed in channels:
            status = "[OK]" if int(successful) > 0 else ("[WARN]" if int(failed) > 0 else "[SKIP]")
            print(f"{status} {channel_name}")
            print(f"   Processed: {processed} | Successful: {successful} | Failed: {failed}")

        print()

    # Model usage analysis
    print("MODEL USAGE ANALYSIS")
    print("-" * 80)

    # Find which channels used which model
    single_model_channels = []
    multi_model_channels = []

    for match in re.finditer(r'Processing channel \[channel_name=([^,]+)', content):
        channel_name = match.group(1)
        start_pos = match.start()
        
        # Look ahead for model initialization
        next_section = content[start_pos:start_pos+2000]
        if 'Initializing single-model LLM service' in next_section:
            single_model_channels.append(channel_name)
        elif 'Initializing multi-model LLM service' in next_section:
            multi_model_channels.append(channel_name)

    print(f"Single-model channels ({len(single_model_channels)}):")
    if single_model_channels:
        for ch in single_model_channels:
            print(f"  • {ch}")
    else:
        print("  (none)")

    print()
    print(f"Multi-model channels ({len(multi_model_channels)}):")
    if multi_model_channels:
        for ch in multi_model_channels:
            print(f"  • {ch}")
    else:
        print("  (none)")

    print()

    # Cost analysis
    print("COST ANALYSIS")
    print("-" * 80)

    cost_estimates = re.findall(r'cost_estimate=([\d.]+)', content)
    if cost_estimates:
        costs = [float(c) for c in cost_estimates]
        total_cost = sum(costs)
        avg_cost = total_cost / len(costs) if costs else 0
        print(f"Total estimated cost: ${total_cost:.4f}")
        print(f"Average cost per video: ${avg_cost:.4f}")
        print(f"Min cost: ${min(costs):.4f}")
        print(f"Max cost: ${max(costs):.4f}")
        
        # Projected costs
        if is_single_video and len(costs) > 0:
            # For single video, show cost per video
            avg_per_video = avg_cost
            print(f"\nProjected costs:")
            print(f"  Per video: ${avg_per_video:.4f}")
            print(f"  10 videos: ${avg_per_video * 10:.2f}")
            print(f"  100 videos: ${avg_per_video * 100:.2f}")
        elif videos_processed > 0:
            # For channel monitoring, show daily/monthly projections
            daily_projection = (total_cost / videos_processed) * 50  # Assume 50 videos/day
            monthly_projection = daily_projection * 30
            print(f"\nProjected costs:")
            print(f"  Daily (50 videos): ${daily_projection:.2f}")
            print(f"  Monthly: ${monthly_projection:.2f}")
    else:
        print("No cost data found in logs")

    print()

    # Processing time analysis
    print("PROCESSING TIME ANALYSIS")
    print("-" * 80)

    # Extract timestamps from log entries
    timestamp_pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'
    timestamps = re.findall(timestamp_pattern, content)
    
    if timestamps and len(timestamps) >= 2:
        try:
            # Parse first and last timestamps
            first_time = datetime.strptime(timestamps[0], '%Y-%m-%d %H:%M:%S')
            last_time = datetime.strptime(timestamps[-1], '%Y-%m-%d %H:%M:%S')
            
            # Calculate total run duration
            duration = (last_time - first_time).total_seconds()
            
            print(f"Run started: {first_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Run ended: {last_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Total run duration: {duration:.1f}s ({duration/60:.1f} minutes)")
            
            # Also show per-video processing times if available
            processing_times = re.findall(r'processing_time_seconds=([\d.]+)', content)
            if processing_times:
                times = [float(t) for t in processing_times]
                avg_time = sum(times) / len(times) if times else 0
                print(f"\nPer-video processing times:")
                print(f"  Videos processed: {len(times)}")
                print(f"  Average time per video: {avg_time:.1f}s")
                print(f"  Min time: {min(times):.1f}s")
                print(f"  Max time: {max(times):.1f}s")
                print(f"  Total video processing: {sum(times):.1f}s ({sum(times)/60:.1f} minutes)")
        except ValueError as e:
            print(f"Error parsing timestamps: {e}")
    else:
        print("Insufficient timestamp data in logs")

    print()

    # Issues and warnings
    print("ISSUES AND WARNINGS")
    print("-" * 80)

    errors = re.findall(r'ERROR.*', content)
    warnings = re.findall(r'WARNING.*members-only.*', content)

    print(f"Members-only warnings: {len(warnings)}")
    if warnings:
        for w in warnings[:5]:  # Show first 5
            print(f"  • {w[:100]}...")

    if errors:
        print(f"\nOther errors: {len(errors)}")
        for e in errors[:5]:  # Show first 5
            print(f"  • {e[:100]}...")

    print()

    # Language support
    print("LANGUAGE SUPPORT")
    print("-" * 80)

    if is_single_video:
        # For single video, just show the language once
        lang_match = re.search(r'original_language=([a-z]{2,3})(?:[,\s\]])', content)
        if lang_match:
            print(f"  Language: {lang_match.group(1)}")
        else:
            print("  No language data found")
    else:
        # For channel monitoring, count languages across multiple videos
        languages = re.findall(r'original_language=([a-z]{2,3})(?:[,\s\]])', content)
        lang_counts = defaultdict(int)
        for lang in languages:
            # Filter out common false positives
            if lang not in ['true', 'false', 'none']:
                lang_counts[lang] += 1

        if lang_counts:
            for lang, count in sorted(lang_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  {lang}: {count} videos")
        else:
            print("  No language data found")

    print()
    print("=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)


def main():
    """Main entry point"""
    # Parse command line arguments
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        
        if arg in ['--help', '-h']:
            print(__doc__)
            sys.exit(0)
        
        elif arg == '--list':
            list_logs()
            sys.exit(0)
        
        elif arg == '--all':
            # Analyze all log files
            log_files = get_all_logs()
            if not log_files:
                print("❌ No log files found")
                sys.exit(1)
            
            print(f"Found {len(log_files)} log file(s)\n")
            for i, log_file in enumerate(log_files, 1):
                print(f"\n{'='*80}")
                print(f"LOG FILE {i}/{len(log_files)}")
                print(f"{'='*80}\n")
                content = analyze_log(log_file)
                print_analysis(content, log_file)
                
                if i < len(log_files):
                    print("\n" + "="*80)
                    print("Press Enter to continue to next log file...")
                    input()
        
        else:
            # Analyze specific log file
            log_path = Path(arg)
            if not log_path.exists():
                print(f"❌ Error: Log file not found: {log_path}")
                sys.exit(1)
            
            content = analyze_log(log_path)
            print_analysis(content, log_path)
    
    else:
        # Analyze latest log file
        log_path = find_latest_log()
        print(f"Analyzing latest log file...\n")
        content = analyze_log(log_path)
        print_analysis(content, log_path)


if __name__ == "__main__":
    main()
