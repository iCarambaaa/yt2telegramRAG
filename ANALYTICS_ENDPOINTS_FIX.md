# Analytics Endpoints Fix

## Problem
The Analytics page was showing "Internal Server Error" because the frontend was calling API endpoints that didn't exist:
- `/api/analytics/metrics`
- `/api/analytics/performance`
- `/api/analytics/costs`
- `/api/analytics/trends`

## Solution
Added all missing endpoints to `gui/api/routers/analytics.py`:

### 1. `/api/analytics/metrics` (GET)
Returns real-time system metrics:
- Overview: total videos, active channels, queue size, today's cost, avg processing time, success rate
- Real-time: videos processed last hour, processing rate, system load, memory/disk usage
- Alerts: system alerts (placeholder for now)

**Query Parameters:**
- `timeRange`: "1h", "24h", "7d", "30d" (default: "24h")

### 2. `/api/analytics/performance` (GET)
Returns performance metrics and chart data:
- Processing times over time
- Response times (placeholder)
- Throughput data (placeholder)
- Summary statistics (avg, max, min processing times)

**Query Parameters:**
- `timeRange`: "1h", "24h", "7d", "30d" (default: "24h")

### 3. `/api/analytics/costs` (GET)
Returns cost analysis data:
- Total cost for time range
- Cost breakdown by model
- Cost breakdown by channel
- Daily cost trend
- Daily average and monthly projection

**Query Parameters:**
- `timeRange`: "1h", "24h", "7d", "30d" (default: "24h")

### 4. `/api/analytics/trends` (GET)
Returns processing trends and patterns:
- Daily trends: videos processed, avg processing time, success rate
- Hourly trends (placeholder)
- Summary: total videos, avg daily videos, trend direction

**Query Parameters:**
- `timeRange`: "7d", "30d", "24h" (default: "7d")

## Data Sources
All endpoints query real data from SQLite databases in `yt2telegram/downloads/`:
- Video counts and processing metrics
- Cost estimates from actual processing
- Processing times from database records
- Success rates based on summary presence

## Testing
The backend server should auto-reload with the new endpoints. Refresh the Analytics page in your browser to see real data instead of errors.

### Expected Results:
- **Overview tab**: Shows real metrics for active channels, videos processed, costs
- **Channels tab**: Already working with real data
- **Performance tab**: Shows processing time trends
- **Costs tab**: Shows cost breakdown by model and channel
- **Trends tab**: Shows daily processing patterns

## Notes
- Some metrics are placeholders (system load, memory usage) as they require additional monitoring
- WebSocket connections for real-time updates are not yet implemented
- Alert system is placeholder - would need separate implementation
- All data is read-only from existing databases
