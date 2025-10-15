#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aggregate log analyzer for YouTube to Telegram runs

Analyzes multiple log files over time periods with intelligent aggregation.

Usage:
    python analyze_aggregate.py --last3     # Last 3 days
    python analyze_aggregate.py --last7     # Last 7 days
    python analyze_aggregate.py --last30    # Last 30 days
    python analyze_aggregate.py --last365   # Last 365 days
"""

import re
import sys
import os
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Set, Tuple

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    try:
        # Try to set console to UTF-8
        os.system('chcp 65001 > nul 2>&1')
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass


def get_logs_from_last_days(days: int) -> List[Path]:
    """Get log files from the last N days"""
    log_dir = Path('logs')
    if not log_dir.exists():
        return []
    
    cutoff_time = datetime.now() - timedelta(days=days)
    log_files = []
    
    for log_file in log_dir.glob('run_*.log'):
        mod_time = datetime.fromtimestamp(log_file.stat().st_mtime)
        if mod_time >= cutoff_time:
            log_files.append(log_file)
    
    return sorted(log_files, key=lambda p: p.stat().st_mtime)


def extract_log_date(log_path: Path) -> datetime:
    """Extract date from log filename"""
    filename = log_path.name
    if match := re.search(r'run_(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})\.log', filename):
        timestamp_str = match.group(1)
        return datetime.strptime(timestamp_str, '%Y-%m-%d_%H-%M-%S')
    return datetime.fromtimestamp(log_path.stat().st_mtime)


def analyze_aggregate(log_files: List[Path], time_period: int):
    """Perform sophisticated aggregate analysis"""
    # Set UTF-8 encoding for Windows console
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass
    
    if not log_files:
        print("No log files found for the specified time period")
        return
    
    # Calculate date range (header will be printed by print_aggregate_analysis)
    oldest = extract_log_date(log_files[0])
    newest = extract_log_date(log_files[-1])
    days_covered = (newest - oldest).days + 1
    
    # Aggregate data structures
    all_channels: Set[str] = set()
    channel_first_seen: Dict[str, datetime] = {}
    channel_stats: Dict[str, Dict] = defaultdict(lambda: {
        'processed': 0,
        'successful': 0,
        'failed': 0
    })
    
    # Model tracking per channel
    channel_models: Dict[str, List[Tuple[datetime, str]]] = defaultdict(list)
    
    # Cost tracking
    all_costs: List[float] = []
    
    # Processing time tracking
    all_processing_times: List[float] = []
    run_durations: List[float] = []
    
    # Error tracking
    error_counts: Dict[str, int] = defaultdict(int)
    error_examples: Dict[str, str] = {}
    
    # Language tracking
    language_counts: Dict[str, int] = defaultdict(int)
    
    # Members-only tracking
    members_only_count = 0
    
    # Process each log file
    for log_file in log_files:
        log_date = extract_log_date(log_file)
        
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract channels processed in this run
        for match in re.finditer(r'Processing channel \[channel_name=([^,]+)', content):
            channel_name = match.group(1)
            all_channels.add(channel_name)
            
            if channel_name not in channel_first_seen:
                channel_first_seen[channel_name] = log_date
        
        # Extract per-channel results
        pattern = r'Finished processing channel \[channel_name=([^,]+), processed_count=(\d+), successful_notifications=(\d+), failed_notifications=(\d+)\]'
        for channel_name, processed, successful, failed in re.findall(pattern, content):
            channel_stats[channel_name]['processed'] += int(processed)
            channel_stats[channel_name]['successful'] += int(successful)
            channel_stats[channel_name]['failed'] += int(failed)
        
        # Track model usage per channel
        for match in re.finditer(r'Processing channel \[channel_name=([^,]+)', content):
            channel_name = match.group(1)
            start_pos = match.start()
            next_section = content[start_pos:start_pos+2000]
            
            if 'Initializing single-model LLM service' in next_section:
                channel_models[channel_name].append((log_date, 'single'))
            elif 'Initializing multi-model LLM service' in next_section:
                channel_models[channel_name].append((log_date, 'multi'))
        
        # Extract costs
        costs = [float(c) for c in re.findall(r'cost_estimate=([\d.]+)', content)]
        all_costs.extend(costs)
        
        # Extract processing times
        times = [float(t) for t in re.findall(r'processing_time_seconds=([\d.]+)', content)]
        all_processing_times.extend(times)
        
        # Extract run duration
        timestamps = re.findall(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', content)
        if timestamps and len(timestamps) >= 2:
            try:
                first_time = datetime.strptime(timestamps[0], '%Y-%m-%d %H:%M:%S')
                last_time = datetime.strptime(timestamps[-1], '%Y-%m-%d %H:%M:%S')
                duration = (last_time - first_time).total_seconds()
                if duration > 0:
                    run_durations.append(duration)
            except:
                pass
        
        # Extract errors
        for error in re.findall(r'ERROR.*', content):
            # Normalize error message
            error_key = re.sub(r'\[.*?\]', '', error)[:100]
            error_counts[error_key] += 1
            if error_key not in error_examples:
                error_examples[error_key] = error
        
        # Extract languages
        for lang in re.findall(r'original_language=(\w+)', content):
            if lang not in ['True', 'False']:  # Filter out boolean values
                language_counts[lang] += 1
        
        # Count members-only
        members_only_count += len(re.findall(r'members-only', content))
    
    # Print analysis
    print_aggregate_analysis(
        all_channels, channel_first_seen, channel_stats, channel_models,
        all_costs, all_processing_times, run_durations, error_counts,
        error_examples, language_counts, members_only_count,
        days_covered, oldest, newest, log_files, time_period, len(log_files)
    )


def print_aggregate_analysis(
    all_channels, channel_first_seen, channel_stats, channel_models,
    all_costs, all_processing_times, run_durations, error_counts,
    error_examples, language_counts, members_only_count,
    days_covered, oldest, newest, log_files, time_period, log_count
):
    """Print comprehensive aggregate analysis"""
    
    print("=" * 80)
    print("AGGREGATE LOG ANALYSIS")
    print("=" * 80)
    print(f"Time period: Last {time_period} days")
    print(f"Log files analyzed: {log_count}")
    print(f"Date range: {oldest.strftime('%Y-%m-%d')} to {newest.strftime('%Y-%m-%d')}")
    print(f"Days covered: {days_covered}")
    print()
    
    # Overall statistics
    print("OVERALL STATISTICS")
    print("-" * 80)
    
    total_channels_seen = len(all_channels)
    # Count only channels that actually had activity (processed, successful, or failed > 0)
    channels_with_activity = sum(1 for stats in channel_stats.values() 
                                 if stats['processed'] > 0 or stats['successful'] > 0 or stats['failed'] > 0)
    total_videos_successful = sum(stats['successful'] for stats in channel_stats.values())
    total_videos_processed = sum(stats['processed'] for stats in channel_stats.values())
    total_videos_failed = sum(stats['failed'] for stats in channel_stats.values())
    
    # Calculate total new videos found (successful + failed)
    total_new_videos = total_videos_successful + total_videos_failed
    
    print(f"Total channels monitored: {total_channels_seen}")
    print(f"Channels with activity: {channels_with_activity}")
    print(f"Total new videos found: {total_new_videos}")
    print(f"Successfully delivered: {total_videos_successful}")
    print(f"Failed/Skipped: {total_videos_failed}")
    print(f"  └─ Members-only detected: {members_only_count}")
    print(f"Videos fully processed: {total_videos_processed}")
    print()
    
    # New channels
    print("NEW CHANNELS")
    print("-" * 80)
    new_channels = [(name, date) for name, date in channel_first_seen.items() 
                    if date > oldest]
    
    if new_channels:
        for channel_name, join_date in sorted(new_channels, key=lambda x: x[1]):
            print(f"  + {channel_name} (joined {join_date.strftime('%Y-%m-%d')})")
    else:
        print("  No new channels in this period")
    print()
    
    # Per-channel breakdown (aggregated)
    print("PER-CHANNEL BREAKDOWN (AGGREGATED)")
    print("-" * 80)
    
    channels_with_failures = []
    
    for channel_name in sorted(channel_stats.keys()):
        stats = channel_stats[channel_name]
        total = stats['processed']
        successful = stats['successful']
        failed = stats['failed']
        
        if successful > 0:
            status = "[OK]"
        elif failed > 0:
            status = "[WARN]"
        else:
            status = "[SKIP]"
        
        print(f"{status} {channel_name}")
        print(f"   Total processed: {total} | Successful: {successful} | Failed: {failed}")
        
        # Track channels with failures for detailed breakdown
        if failed > 0:
            channels_with_failures.append(channel_name)
    print()
    
    # Model usage analysis
    print("MODEL USAGE ANALYSIS")
    print("-" * 80)
    
    single_model_channels = set()
    multi_model_channels = set()
    switched_channels = []
    
    for channel_name, model_history in channel_models.items():
        if not model_history:
            continue
        
        models_used = set(m for _, m in model_history)
        
        if len(models_used) > 1:
            # Channel switched models
            switched_channels.append((channel_name, model_history))
        elif 'single' in models_used:
            single_model_channels.add(channel_name)
        elif 'multi' in models_used:
            multi_model_channels.add(channel_name)
    
    print(f"Single-model channels: {len(single_model_channels)}")
    for ch in sorted(single_model_channels):
        print(f"  • {ch}")
    
    print(f"\nMulti-model channels: {len(multi_model_channels)}")
    for ch in sorted(multi_model_channels):
        print(f"  • {ch}")
    
    if switched_channels:
        print(f"\nChannels that switched models: {len(switched_channels)}")
        for channel_name, history in switched_channels:
            changes = []
            prev_model = None
            for date, model in history:
                if model != prev_model:
                    changes.append(f"{model} on {date.strftime('%Y-%m-%d')}")
                    prev_model = model
            print(f"  • {channel_name}: {' -> '.join(changes)}")
    print()
    
    # Cost analysis
    print("COST ANALYSIS")
    print("-" * 80)
    
    if all_costs:
        total_cost = sum(all_costs)
        avg_cost = total_cost / len(all_costs)
        daily_avg_cost = total_cost / days_covered if days_covered > 0 else 0
        monthly_projection = daily_avg_cost * 30
        
        print(f"Total cost: ${total_cost:.4f}")
        print(f"Average cost per video: ${avg_cost:.4f}")
        print(f"Min cost: ${min(all_costs):.4f}")
        print(f"Max cost: ${max(all_costs):.4f}")
        print()
        print(f"Daily average cost: ${daily_avg_cost:.2f}")
        print(f"Projected monthly cost: ${monthly_projection:.2f}")
        
        # Based on actual processing rate
        if days_covered > 0:
            videos_per_day = total_videos_successful / days_covered
            print(f"\nBased on actual rate ({videos_per_day:.1f} videos/day):")
            print(f"  Daily cost: ${daily_avg_cost:.2f}")
            print(f"  Monthly cost: ${monthly_projection:.2f}")
    else:
        print("No cost data available")
    print()
    
    # Processing time analysis
    print("PROCESSING TIME ANALYSIS")
    print("-" * 80)
    
    if all_processing_times:
        avg_time = sum(all_processing_times) / len(all_processing_times)
        print(f"Videos processed: {len(all_processing_times)}")
        print(f"Average time per video: {avg_time:.1f}s")
        print(f"Min time: {min(all_processing_times):.1f}s")
        print(f"Max time: {max(all_processing_times):.1f}s")
        print(f"Total processing time: {sum(all_processing_times):.1f}s ({sum(all_processing_times)/60:.1f} min)")
    
    if run_durations:
        avg_run = sum(run_durations) / len(run_durations)
        print(f"\nRun statistics:")
        print(f"  Total runs: {len(run_durations)}")
        print(f"  Average run duration: {avg_run:.1f}s ({avg_run/60:.1f} min)")
        print(f"  Min run: {min(run_durations):.1f}s")
        print(f"  Max run: {max(run_durations):.1f}s")
    print()
    
    # Failure breakdown by channel
    if channels_with_failures:
        print("FAILURE BREAKDOWN BY CHANNEL")
        print("-" * 80)
        
        for channel_name in channels_with_failures:
            failed_count = channel_stats[channel_name]['failed']
            print(f"\n{channel_name}: {failed_count} failure(s)")
            
            # Extract failure reasons for this channel from logs
            failures_found = set()  # Track unique failures to avoid duplicates
            
            for log_file in log_files:
                with open(log_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Find all members-only for this channel
                # Look for the channel processing section first
                channel_start = content.find(f"Processing channel [channel_name={channel_name}")
                if channel_start != -1:
                    # Find the end of this channel's section (next channel or end of file)
                    next_channel = content.find("Processing channel [channel_name=", channel_start + 1)
                    channel_section = content[channel_start:next_channel] if next_channel != -1 else content[channel_start:]
                    
                    # Now find all members-only in this section
                    members_only_matches = re.findall(
                        r'Skipping permanently members-only video \[video_id=([^,]+), video_title=([^,]+)',
                        channel_section
                    )
                    for video_id, video_title in members_only_matches:
                        video_title = video_title.strip().replace(', reason=permanent_members_only]', '')
                        if video_id not in failures_found:
                            failures_found.add(video_id)
                            print(f"  • Members-only: {video_title[:60]}... (ID: {video_id})")
                
                    # Find all members-first in this section
                    members_first_matches = re.findall(
                        r'Skipping members-first video.*?video_id=([^,]+), video_title=([^,]+)',
                        channel_section
                    )
                    for video_id, video_title in members_first_matches:
                        video_title = video_title.strip()
                        if video_id not in failures_found:
                            failures_found.add(video_id)
                            print(f"  • Members-first: {video_title[:60]}... (ID: {video_id})")
                    
                    # Find other failures in this section
                    failure_matches = re.findall(
                        r'Failed to (\w+).*?video_id=([^,\]]+)',
                        channel_section
                    )
                    for action, video_id in failure_matches:
                        if video_id not in failures_found:
                            failures_found.add(video_id)
                            print(f"  • Failed to {action}: Video ID {video_id}")
        
        print()
    
    # Error analysis
    print("ERROR ANALYSIS")
    print("-" * 80)
    
    if error_counts:
        print(f"Total unique errors: {len(error_counts)}")
        print(f"Total error occurrences: {sum(error_counts.values())}")
        print()
        
        # Sort by frequency
        sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
        
        print("Most frequent errors:")
        for i, (error_key, count) in enumerate(sorted_errors[:10], 1):
            print(f"\n{i}. Occurred {count} time(s):")
            print(f"   {error_examples[error_key][:150]}")
            if len(error_examples[error_key]) > 150:
                print("   ...")
    else:
        print("No errors found")
    print()
    
    # Language support
    print("LANGUAGE SUPPORT")
    print("-" * 80)
    
    if language_counts:
        total_lang_videos = sum(language_counts.values())
        for lang, count in sorted(language_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_lang_videos * 100) if total_lang_videos > 0 else 0
            print(f"  {lang}: {count} videos ({percentage:.1f}%)")
    else:
        print("  No language data available")
    print()
    
    # Daily averages
    print("DAILY AVERAGES")
    print("-" * 80)
    
    if days_covered > 0:
        print(f"Period: {days_covered} days")
        print(f"Videos per day: {total_videos_successful / days_covered:.1f}")
        
        if all_costs:
            print(f"Cost per day: ${sum(all_costs) / days_covered:.2f}")
        
        if all_processing_times:
            print(f"Processing time per day: {sum(all_processing_times) / days_covered / 60:.1f} minutes")
    print()
    
    print("=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nError: Please specify a time period")
        print("Example: python analyze_aggregate.py --last7")
        sys.exit(1)
    
    arg = sys.argv[1]
    
    if arg in ['--help', '-h']:
        print(__doc__)
        sys.exit(0)
    
    # Parse time period
    time_periods = {
        '--last3': 3,
        '--last7': 7,
        '--last30': 30,
        '--last365': 365
    }
    
    if arg not in time_periods:
        print(f"Error: Unknown option '{arg}'")
        print("Valid options: --last3, --last7, --last30, --last365")
        sys.exit(1)
    
    days = time_periods[arg]
    log_files = get_logs_from_last_days(days)
    
    if not log_files:
        print(f"No log files found for the last {days} days")
        sys.exit(1)
    
    analyze_aggregate(log_files, days)


if __name__ == "__main__":
    main()
