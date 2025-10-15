# Log Analysis Tool

This directory contains log files from YouTube to Telegram processing runs and a tool to analyze them.

## Log Files

Log files are automatically created with timestamps when `run.py` executes:
- Format: `run_YYYY-MM-DD_HH-MM-SS.log`
- Location: `logs/`
- Encoding: UTF-8

## Analysis Tool

Use `analyze_log.py` to analyze log files and get comprehensive statistics.

### Usage

```bash
# Analyze the latest log file
python analyze_log.py

# Analyze a specific log file
python analyze_log.py logs/run_2025-10-13_16-41-03.log

# List all available log files
python analyze_log.py --list

# Analyze all log files (interactive)
python analyze_log.py --all

# Show help
python analyze_log.py --help
```

### Time-Based Aggregate Analysis

For analyzing multiple logs over time periods, use the **aggregate analyzer**:

```bash
# Analyze logs from last 3 days (aggregate)
python analyze_aggregate.py --last3

# Analyze logs from last 7 days (aggregate)
python analyze_aggregate.py --last7

# Analyze logs from last 30 days (aggregate)
python analyze_aggregate.py --last30

# Analyze logs from last 365 days (aggregate)
python analyze_aggregate.py --last365
```

The aggregate analyzer provides:
- Combined statistics across all runs
- Distinct vs total channel counts
- New channel detection with join dates
- Aggregated per-channel stats (no duplicates)
- Model switch tracking
- Cost projections based on actual processing rate
- Error frequency analysis
- Daily averages and trends

See `AGGREGATE_ANALYZER_GUIDE.md` for complete documentation.

### What It Analyzes

The tool provides comprehensive analysis including:

- **Overall Statistics**
  - Total channels processed
  - Videos processed vs skipped
  - Members-only content detected
  - Model usage (single vs multi-model)

- **Per-Channel Breakdown**
  - Processing status for each channel
  - Success/failure counts
  - Videos processed per channel

- **Model Usage Analysis**
  - Which channels use single-model
  - Which channels use multi-model
  - Model initialization success rate

- **Cost Analysis**
  - Total estimated cost
  - Average cost per video
  - Min/max costs
  - Projected daily/monthly costs

- **Performance Analysis**
  - Total processing time
  - Average time per video
  - Min/max processing times

- **Language Support**
  - Languages detected
  - Video count per language

- **Issues & Warnings**
  - Members-only content warnings
  - Errors encountered
  - Other warnings

### Example Output

```
================================================================================
COMPREHENSIVE LOG ANALYSIS
================================================================================
Log File: logs\run_2025-10-13_16-41-03.log
Run Time: 2025-10-13 at 16-41-03
File Size: 130,905 bytes (127.8 KB)

OVERALL STATISTICS
--------------------------------------------------------------------------------
Total channels processed: 15
Videos successfully processed: 11
Videos skipped (already processed): 11
Members-only videos detected: 1
Single-model initializations: 1
Multi-model initializations: 14
Multi-model completions: 11

...
```

## Log Retention

- Logs are kept indefinitely by default
- Consider implementing log rotation for long-term use
- Recommended: Keep last 30 days of logs
- Archive older logs if needed for historical analysis

## Troubleshooting

### No log files found
- Ensure you've run `python run.py` at least once
- Check that the `logs/` directory exists

### Encoding errors
- The tool automatically handles UTF-8 encoding
- If issues persist, check your terminal encoding settings

### Analysis shows no data
- Verify the log file contains actual processing data
- Check if the run completed successfully
- Ensure the log file isn't corrupted

## Integration

The log analysis tool can be integrated into:
- CI/CD pipelines for monitoring
- Automated reporting systems
- Cost tracking dashboards
- Performance monitoring tools

## Future Enhancements

Potential improvements:
- JSON export for programmatic access
- Comparison between multiple runs
- Trend analysis over time
- Alert thresholds for costs/errors
- Web-based dashboard
