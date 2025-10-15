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
        return content
    except Exception as e:
        print(f"❌ Error reading log file: {e}")
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

    # Overall statistics
    print("OVERALL STATISTICS")
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

    # Per-channel breakdown
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
        if videos_processed > 0:
            daily_projection = (total_cost / videos_processed) * 50  # Assume 50 videos/day
            monthly_projection = daily_projection * 30
            print(f"Projected daily cost (50 videos): ${daily_projection:.2f}")
            print(f"Projected monthly cost: ${monthly_projection:.2f}")
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

    languages = re.findall(r'original_language=(\w+)', content)
    lang_counts = defaultdict(int)
    for lang in languages:
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
