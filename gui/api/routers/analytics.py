"""
Analytics and statistics API endpoints.

CRITICAL: System metrics and data visualization
DEPENDENCIES: Database manager, existing analytics
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from .auth import get_current_user_dependency, get_optional_user
from utils.logging_config import setup_logging
from services.channel_database_service import ChannelDatabaseService

logger = setup_logging(__name__)

router = APIRouter()

# Initialize channel database service
channel_db_service = ChannelDatabaseService()


class MetricResponse(BaseModel):
    name: str
    value: float
    unit: str
    timestamp: str
    tags: Dict[str, str]


class AnalyticsResponse(BaseModel):
    metrics: List[MetricResponse]
    summary: Dict[str, Any]
    time_range: Dict[str, str]


class ChannelStatsResponse(BaseModel):
    channel_id: str
    channel_name: str
    video_count: int
    total_processing_time: float
    average_cost: float
    last_processed: Optional[str]
    success_rate: float


@router.get("/overview", response_model=AnalyticsResponse)
async def get_analytics_overview(
    days: int = 7,
    current_user: Dict = Depends(get_current_user_dependency())
):
    """Get system analytics overview."""
    
    try:
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        # TODO: Query actual metrics from database
        # Placeholder implementation
        
        metrics = [
            MetricResponse(
                name="videos_processed",
                value=42.0,
                unit="count",
                timestamp=datetime.utcnow().isoformat(),
                tags={"period": f"{days}d"}
            ),
            MetricResponse(
                name="total_cost",
                value=15.75,
                unit="USD",
                timestamp=datetime.utcnow().isoformat(),
                tags={"period": f"{days}d"}
            ),
            MetricResponse(
                name="average_processing_time",
                value=125.5,
                unit="seconds",
                timestamp=datetime.utcnow().isoformat(),
                tags={"period": f"{days}d"}
            ),
            MetricResponse(
                name="success_rate",
                value=0.95,
                unit="percentage",
                timestamp=datetime.utcnow().isoformat(),
                tags={"period": f"{days}d"}
            )
        ]
        
        summary = {
            "total_videos": 42,
            "active_channels": 5,
            "total_cost": 15.75,
            "average_cost_per_video": 0.375,
            "success_rate": 95.0
        }
        
        logger.info("Retrieved analytics overview", 
                   days=days,
                   metrics_count=len(metrics),
                   user=current_user["username"])
        
        return AnalyticsResponse(
            metrics=metrics,
            summary=summary,
            time_range={
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            }
        )
        
    except Exception as e:
        logger.error("Failed to get analytics overview", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analytics"
        )


@router.get("/channels")
async def get_channel_statistics(
    timeRange: str = Query("7d", description="Time range for analytics"),
    current_user: Optional[Dict] = Depends(get_optional_user)
):
    """Get statistics for all channels with analytics data."""
    
    try:
        import sqlite3
        from pathlib import Path
        from datetime import datetime, timedelta
        
        downloads_dir = Path("yt2telegram/downloads")
        channels = []
        
        # Parse time range
        days = 7
        if timeRange.endswith('d'):
            days = int(timeRange[:-1])
        
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        if downloads_dir.exists():
            for db_file in downloads_dir.glob("*.db"):
                try:
                    conn = sqlite3.connect(db_file)
                    conn.row_factory = sqlite3.Row
                    
                    channel_name = db_file.stem
                    
                    # Get channel statistics
                    cursor = conn.execute("""
                        SELECT 
                            COUNT(*) as videos_processed,
                            SUM(CASE WHEN cost_estimate IS NOT NULL THEN cost_estimate ELSE 0 END) as total_cost,
                            AVG(CASE WHEN cost_estimate IS NOT NULL THEN cost_estimate ELSE 0 END) as avg_cost_per_video,
                            AVG(CASE WHEN processing_time_seconds IS NOT NULL THEN processing_time_seconds ELSE 0 END) as avg_processing_time,
                            SUM(CASE WHEN summary IS NOT NULL AND summary != '' THEN 1 ELSE 0 END) as success_count,
                            MAX(processed_at) as last_processed,
                            MAX(channel_id) as channel_id
                        FROM videos
                        WHERE DATE(processed_at) >= ?
                    """, (cutoff_date,))
                    
                    stats = cursor.fetchone()
                    
                    videos_processed = stats['videos_processed']
                    success_rate = (stats['success_count'] / videos_processed) if videos_processed > 0 else 0.0
                    
                    # Get processing trend
                    cursor = conn.execute("""
                        SELECT 
                            DATE(processed_at) as date,
                            COUNT(*) as count,
                            SUM(CASE WHEN cost_estimate IS NOT NULL THEN cost_estimate ELSE 0 END) as cost
                        FROM videos
                        WHERE DATE(processed_at) >= ?
                        GROUP BY DATE(processed_at)
                        ORDER BY date DESC
                    """, (cutoff_date,))
                    
                    processing_trend = [
                        {"date": row['date'], "count": row['count'], "cost": round(row['cost'] or 0.0, 2)}
                        for row in cursor.fetchall()
                    ]
                    
                    # Get model usage
                    cursor = conn.execute("""
                        SELECT 
                            primary_model,
                            COUNT(*) as count,
                            SUM(CASE WHEN cost_estimate IS NOT NULL THEN cost_estimate ELSE 0 END) as cost,
                            AVG(CASE WHEN processing_time_seconds IS NOT NULL THEN processing_time_seconds ELSE 0 END) as avg_time
                        FROM videos
                        WHERE DATE(processed_at) >= ? AND primary_model IS NOT NULL
                        GROUP BY primary_model
                    """, (cutoff_date,))
                    
                    model_usage = {}
                    for row in cursor.fetchall():
                        model_usage[row['primary_model']] = {
                            "count": row['count'],
                            "cost": round(row['cost'] or 0.0, 2),
                            "avg_time": round(row['avg_time'] or 0.0, 1)
                        }
                    
                    # Get error rate and queue size (placeholder)
                    error_rate = 1.0 - success_rate
                    queue_size = 0  # Would need separate queue tracking
                    
                    channels.append({
                        "channel_id": stats['channel_id'] or channel_name,
                        "channel_name": channel_name,
                        "videos_processed": videos_processed,
                        "total_cost": round(stats['total_cost'] or 0.0, 2),
                        "avg_cost_per_video": round(stats['avg_cost_per_video'] or 0.0, 4),
                        "avg_processing_time": round(stats['avg_processing_time'] or 0.0, 1),
                        "success_rate": round(success_rate, 2),
                        "last_processed": stats['last_processed'],
                        "processing_trend": processing_trend,
                        "model_usage": model_usage,
                        "error_rate": round(error_rate, 2),
                        "queue_size": queue_size
                    })
                    
                    conn.close()
                    
                except Exception as e:
                    logger.error(f"Error processing database {db_file.name}", error=str(e))
        
        logger.info("Retrieved channel statistics", 
                   channels=len(channels),
                   time_range=timeRange,
                   user=current_user["username"])
        
        return {"channels": channels}
        
    except Exception as e:
        logger.error("Failed to get channel statistics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve channel statistics"
        )


@router.get("/channels/{channel_name}/metrics", response_model=AnalyticsResponse)
async def get_channel_metrics(
    channel_name: str,
    days: int = 30,
    current_user: Dict = Depends(get_current_user_dependency())
):
    """Get detailed metrics for a specific channel."""
    
    try:
        # TODO: Query channel-specific metrics
        # Placeholder implementation
        
        metrics = [
            MetricResponse(
                name="videos_processed",
                value=15.0,
                unit="count",
                timestamp=datetime.utcnow().isoformat(),
                tags={"channel": channel_name, "period": f"{days}d"}
            ),
            MetricResponse(
                name="processing_cost",
                value=5.25,
                unit="USD",
                timestamp=datetime.utcnow().isoformat(),
                tags={"channel": channel_name, "period": f"{days}d"}
            )
        ]
        
        summary = {
            "channel_name": channel_name,
            "videos_processed": 15,
            "total_cost": 5.25,
            "average_cost": 0.35,
            "success_rate": 97.0
        }
        
        logger.info("Retrieved channel metrics", 
                   channel=channel_name,
                   days=days,
                   user=current_user["username"])
        
        return AnalyticsResponse(
            metrics=metrics,
            summary=summary,
            time_range={
                "start": (datetime.utcnow() - timedelta(days=days)).isoformat(),
                "end": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        logger.error("Failed to get channel metrics", 
                    channel=channel_name, 
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve channel metrics"
        )


@router.get("/costs", response_model=Dict[str, Any])
async def get_cost_analysis(
    days: int = 30,
    current_user: Dict = Depends(get_current_user_dependency())
):
    """Get cost analysis and breakdown."""
    
    try:
        # TODO: Query actual cost data
        # Placeholder implementation
        
        cost_analysis = {
            "total_cost": 47.85,
            "period_days": days,
            "cost_by_model": {
                "gpt-4o-mini": 32.50,
                "claude-3-haiku": 15.35
            },
            "cost_by_channel": {
                "twominutepapers": 18.75,
                "isaac_arthur": 12.40,
                "other": 16.70
            },
            "daily_average": 1.60,
            "projected_monthly": 48.00,
            "cost_trends": [
                {"date": "2025-09-23", "cost": 1.25},
                {"date": "2025-09-24", "cost": 2.10},
                {"date": "2025-09-25", "cost": 0.85},
                {"date": "2025-09-26", "cost": 1.95},
                {"date": "2025-09-27", "cost": 1.40},
                {"date": "2025-09-28", "cost": 2.30},
                {"date": "2025-09-29", "cost": 1.75}
            ]
        }
        
        logger.info("Retrieved cost analysis", 
                   days=days,
                   total_cost=cost_analysis["total_cost"],
                   user=current_user["username"])
        
        return cost_analysis
        
    except Exception as e:
        logger.error("Failed to get cost analysis", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cost analysis"
        )


@router.get("/performance", response_model=Dict[str, Any])
async def get_performance_metrics(
    current_user: Dict = Depends(get_current_user_dependency())
):
    """Get system performance metrics."""
    
    try:
        # TODO: Query actual performance data
        # Placeholder implementation
        
        performance_metrics = {
            "api_response_times": {
                "average": 125.5,
                "p95": 250.0,
                "p99": 500.0
            },
            "database_performance": {
                "query_time_avg": 15.2,
                "connection_pool_usage": 0.65
            },
            "websocket_stats": {
                "active_connections": 12,
                "messages_per_second": 2.5
            },
            "system_resources": {
                "cpu_usage": 0.35,
                "memory_usage": 0.68,
                "disk_usage": 0.42
            }
        }
        
        logger.info("Retrieved performance metrics", user=current_user["username"])
        
        return performance_metrics
        
    except Exception as e:
        logger.error("Failed to get performance metrics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve performance metrics"
        )


# Database Browser Endpoints

@router.get("/database/videos", response_model=Dict[str, Any])
async def get_video_records(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    channel_id: Optional[str] = Query(None, description="Filter by channel ID"),
    search: Optional[str] = Query(None, description="Search in title or content"),
    sort_by: str = Query("processed_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    date_from: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    has_summary: Optional[bool] = Query(None, description="Filter by summary presence"),
    summarization_method: Optional[str] = Query(None, description="Filter by summarization method"),
    current_user: Dict = Depends(get_current_user_dependency())
):
    """Get video records with advanced filtering and pagination."""
    
    try:
        import sqlite3
        from pathlib import Path
        import json
        
        downloads_dir = Path("yt2telegram/downloads")
        all_videos = []
        
        # Scan all database files or specific channel
        if downloads_dir.exists():
            db_files = []
            if channel_id:
                # Try to find database by channel_id
                db_file = downloads_dir / f"{channel_id}.db"
                if db_file.exists():
                    db_files = [db_file]
            else:
                db_files = list(downloads_dir.glob("*.db"))
            
            for db_file in db_files:
                try:
                    conn = sqlite3.connect(db_file)
                    conn.row_factory = sqlite3.Row
                    
                    channel_name = db_file.stem
                    
                    # Build query with filters
                    where_clauses = []
                    params = []
                    
                    if search:
                        where_clauses.append("(title LIKE ? OR summary LIKE ?)")
                        params.extend([f"%{search}%", f"%{search}%"])
                    
                    if date_from:
                        where_clauses.append("DATE(processed_at) >= ?")
                        params.append(date_from)
                    
                    if date_to:
                        where_clauses.append("DATE(processed_at) <= ?")
                        params.append(date_to)
                    
                    if has_summary is not None:
                        if has_summary:
                            where_clauses.append("(summary IS NOT NULL AND summary != '')")
                        else:
                            where_clauses.append("(summary IS NULL OR summary = '')")
                    
                    if summarization_method:
                        where_clauses.append("summarization_method = ?")
                        params.append(summarization_method)
                    
                    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
                    
                    query = f"""
                        SELECT 
                            id,
                            title,
                            channel_id,
                            published_at,
                            processed_at,
                            summarization_method,
                            primary_model,
                            secondary_model,
                            synthesis_model,
                            processing_time_seconds,
                            cost_estimate,
                            token_usage_json,
                            CASE WHEN summary IS NOT NULL AND summary != '' THEN 1 ELSE 0 END as has_summary,
                            LENGTH(summary) as summary_length,
                            fallback_used
                        FROM videos
                        WHERE {where_sql}
                    """
                    
                    cursor = conn.execute(query, params)
                    
                    for row in cursor.fetchall():
                        # Parse token usage
                        token_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
                        if row['token_usage_json']:
                            try:
                                token_data = json.loads(row['token_usage_json'])
                                if isinstance(token_data, dict):
                                    # Handle multi-model format
                                    if 'primary' in token_data:
                                        token_usage["input_tokens"] = token_data.get('primary', {}).get('input', 0)
                                        token_usage["output_tokens"] = token_data.get('primary', {}).get('output', 0)
                                    else:
                                        token_usage = token_data
                                    token_usage["total_tokens"] = token_usage.get("input_tokens", 0) + token_usage.get("output_tokens", 0)
                            except:
                                pass
                        
                        all_videos.append({
                            "id": row['id'],
                            "title": row['title'],
                            "channel_id": row['channel_id'] or channel_name,
                            "channel_name": channel_name,
                            "published_at": row['published_at'],
                            "processed_at": row['processed_at'],
                            "summarization_method": row['summarization_method'] or 'single',
                            "primary_model": row['primary_model'],
                            "secondary_model": row['secondary_model'],
                            "synthesis_model": row['synthesis_model'],
                            "processing_time_seconds": row['processing_time_seconds'] or 0.0,
                            "cost_estimate": row['cost_estimate'] or 0.0,
                            "token_usage": token_usage,
                            "has_summary": bool(row['has_summary']),
                            "summary_length": row['summary_length'] or 0,
                            "fallback_used": bool(row['fallback_used'])
                        })
                    
                    conn.close()
                    
                except Exception as e:
                    logger.error(f"Error reading database {db_file.name}", error=str(e))
        
        # Sort videos
        sort_key = sort_by
        reverse = (sort_order.lower() == "desc")
        
        try:
            all_videos.sort(key=lambda x: x.get(sort_key) or "", reverse=reverse)
        except:
            # Fallback to processed_at if sort fails
            all_videos.sort(key=lambda x: x.get("processed_at") or "", reverse=True)
        
        # Paginate
        total_count = len(all_videos)
        offset = (page - 1) * page_size
        paginated_videos = all_videos[offset:offset + page_size]
        
        logger.info("Retrieved video records", 
                   page=page, 
                   page_size=page_size, 
                   total=total_count,
                   returned=len(paginated_videos),
                   user=current_user["username"])
        
        return {
            "videos": paginated_videos,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": (total_count + page_size - 1) // page_size if total_count > 0 else 0,
                "has_next": total_count > page * page_size,
                "has_previous": page > 1
            },
            "filters_applied": {
                "channel_id": channel_id,
                "search": search,
                "sort_by": sort_by,
                "sort_order": sort_order,
                "date_from": date_from,
                "date_to": date_to,
                "has_summary": has_summary,
                "summarization_method": summarization_method
            }
        }
        
    except Exception as e:
        logger.error("Failed to get video records", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve video records"
        )


@router.get("/database/videos/{video_id}", response_model=Dict[str, Any])
async def get_video_details(
    video_id: str,
    current_user: Dict = Depends(get_current_user_dependency())
):
    """Get detailed information for a specific video."""
    
    try:
        import sqlite3
        from pathlib import Path
        
        downloads_dir = Path("yt2telegram/downloads")
        
        # Search for video across all databases
        if downloads_dir.exists():
            for db_file in downloads_dir.glob("*.db"):
                try:
                    conn = sqlite3.connect(db_file)
                    conn.row_factory = sqlite3.Row
                    
                    cursor = conn.execute("""
                        SELECT * FROM videos WHERE id = ?
                    """, (video_id,))
                    
                    row = cursor.fetchone()
                    
                    if row:
                        video_details = dict(row)
                        video_details["channel_name"] = db_file.stem
                        
                        # Add metadata if available
                        video_details["metadata"] = {
                            "duration": video_details.get("duration", "Unknown"),
                            "view_count": video_details.get("view_count", 0),
                            "like_count": video_details.get("like_count", 0),
                            "comment_count": video_details.get("comment_count", 0)
                        }
                        
                        conn.close()
                        
                        logger.info("Retrieved video details", 
                                   video_id=video_id, 
                                   channel=db_file.stem,
                                   user=current_user["username"])
                        
                        return video_details
                    
                    conn.close()
                    
                except Exception as e:
                    logger.error(f"Error searching database {db_file.name}", error=str(e))
        
        # Video not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video {video_id} not found in any database"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get video details", video_id=video_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve video details"
        )


@router.get("/database/statistics", response_model=Dict[str, Any])
async def get_database_statistics(
    current_user: Dict = Depends(get_current_user_dependency())
):
    """Get comprehensive database statistics and summary views."""
    
    try:
        import sqlite3
        from pathlib import Path
        from datetime import datetime, timedelta
        
        downloads_dir = Path("yt2telegram/downloads")
        
        # Initialize aggregated statistics
        total_videos = 0
        total_channels = 0
        total_cost = 0.0
        total_processing_time = 0.0
        processed_today = 0
        processing_errors = 0
        
        by_channel = []
        by_model = {}
        daily_counts = {}
        
        today = datetime.now().date()
        
        # Scan all database files
        if downloads_dir.exists():
            for db_file in downloads_dir.glob("*.db"):
                try:
                    conn = sqlite3.connect(db_file)
                    conn.row_factory = sqlite3.Row
                    
                    channel_name = db_file.stem
                    total_channels += 1
                    
                    # Get channel statistics
                    cursor = conn.execute("""
                        SELECT 
                            COUNT(*) as video_count,
                            SUM(CASE WHEN cost_estimate IS NOT NULL THEN cost_estimate ELSE 0 END) as total_cost,
                            AVG(CASE WHEN cost_estimate IS NOT NULL THEN cost_estimate ELSE 0 END) as avg_cost,
                            AVG(CASE WHEN processing_time_seconds IS NOT NULL THEN processing_time_seconds ELSE 0 END) as avg_time,
                            SUM(CASE WHEN summary IS NOT NULL AND summary != '' THEN 1 ELSE 0 END) as with_summary,
                            MAX(channel_id) as channel_id
                        FROM videos
                    """)
                    
                    channel_stats = cursor.fetchone()
                    video_count = channel_stats['video_count']
                    channel_cost = channel_stats['total_cost'] or 0.0
                    
                    total_videos += video_count
                    total_cost += channel_cost
                    
                    # Calculate success rate
                    success_rate = (channel_stats['with_summary'] / video_count) if video_count > 0 else 0.0
                    
                    by_channel.append({
                        "channel_id": channel_stats['channel_id'] or channel_name,
                        "channel_name": channel_name,
                        "video_count": video_count,
                        "total_cost": round(channel_cost, 2),
                        "avg_cost_per_video": round(channel_stats['avg_cost'] or 0.0, 4),
                        "success_rate": round(success_rate, 2)
                    })
                    
                    # Get model usage
                    cursor = conn.execute("""
                        SELECT 
                            primary_model,
                            COUNT(*) as usage_count,
                            SUM(CASE WHEN cost_estimate IS NOT NULL THEN cost_estimate ELSE 0 END) as total_cost,
                            AVG(CASE WHEN processing_time_seconds IS NOT NULL THEN processing_time_seconds ELSE 0 END) as avg_time
                        FROM videos
                        WHERE primary_model IS NOT NULL
                        GROUP BY primary_model
                    """)
                    
                    for row in cursor.fetchall():
                        model = row['primary_model']
                        if model not in by_model:
                            by_model[model] = {
                                "usage_count": 0,
                                "total_cost": 0.0,
                                "total_time": 0.0,
                                "count": 0
                            }
                        by_model[model]["usage_count"] += row['usage_count']
                        by_model[model]["total_cost"] += row['total_cost'] or 0.0
                        by_model[model]["total_time"] += (row['avg_time'] or 0.0) * row['usage_count']
                        by_model[model]["count"] += row['usage_count']
                    
                    # Get daily counts
                    cursor = conn.execute("""
                        SELECT 
                            DATE(processed_at) as date,
                            COUNT(*) as count,
                            SUM(CASE WHEN cost_estimate IS NOT NULL THEN cost_estimate ELSE 0 END) as cost
                        FROM videos
                        WHERE processed_at IS NOT NULL
                        GROUP BY DATE(processed_at)
                        ORDER BY date DESC
                        LIMIT 7
                    """)
                    
                    for row in cursor.fetchall():
                        date_str = row['date']
                        if date_str not in daily_counts:
                            daily_counts[date_str] = {"count": 0, "cost": 0.0}
                        daily_counts[date_str]["count"] += row['count']
                        daily_counts[date_str]["cost"] += row['cost'] or 0.0
                    
                    # Count processed today
                    cursor = conn.execute("""
                        SELECT COUNT(*) as count
                        FROM videos
                        WHERE DATE(processed_at) = DATE('now')
                    """)
                    processed_today += cursor.fetchone()['count']
                    
                    # Count processing errors (videos without summaries)
                    cursor = conn.execute("""
                        SELECT COUNT(*) as count
                        FROM videos
                        WHERE summary IS NULL OR summary = ''
                    """)
                    processing_errors += cursor.fetchone()['count']
                    
                    # Get average processing time
                    cursor = conn.execute("""
                        SELECT AVG(processing_time_seconds) as avg_time
                        FROM videos
                        WHERE processing_time_seconds IS NOT NULL
                    """)
                    avg_time = cursor.fetchone()['avg_time']
                    if avg_time:
                        total_processing_time += avg_time * video_count
                    
                    conn.close()
                    
                except Exception as e:
                    logger.error(f"Error processing database {db_file.name}", error=str(e))
        
        # Calculate averages
        avg_processing_time = (total_processing_time / total_videos) if total_videos > 0 else 0.0
        
        # Format model statistics
        by_model_list = []
        for model, stats in by_model.items():
            by_model_list.append({
                "model": model,
                "usage_count": stats["usage_count"],
                "total_cost": round(stats["total_cost"], 2),
                "avg_cost": round(stats["total_cost"] / stats["usage_count"], 4) if stats["usage_count"] > 0 else 0.0,
                "avg_processing_time": round(stats["total_time"] / stats["count"], 1) if stats["count"] > 0 else 0.0
            })
        
        # Format daily counts
        daily_counts_list = [
            {"date": date, "count": data["count"], "cost": round(data["cost"], 2)}
            for date, data in sorted(daily_counts.items(), reverse=True)
        ]
        
        # Calculate success rate trend
        success_rate_trend = [
            {"date": item["date"], "success_rate": 0.95}  # Placeholder - would need more complex query
            for item in daily_counts_list
        ]
        
        # Calculate storage info
        total_db_size = sum(f.stat().st_size for f in downloads_dir.glob("*.db")) / (1024 * 1024) if downloads_dir.exists() else 0.0
        
        stats = {
            "overview": {
                "total_videos": total_videos,
                "total_channels": total_channels,
                "processed_today": processed_today,
                "processing_errors": processing_errors,
                "total_cost": round(total_cost, 2),
                "avg_processing_time": round(avg_processing_time, 1)
            },
            "by_channel": sorted(by_channel, key=lambda x: x["video_count"], reverse=True),
            "by_model": sorted(by_model_list, key=lambda x: x["usage_count"], reverse=True),
            "processing_trends": {
                "daily_counts": daily_counts_list,
                "success_rate_trend": success_rate_trend
            },
            "storage_info": {
                "database_size_mb": round(total_db_size, 1),
                "subtitle_storage_mb": round(total_db_size * 0.3, 1),  # Estimate
                "summary_storage_mb": round(total_db_size * 0.1, 1),  # Estimate
                "growth_rate_mb_per_day": round(total_db_size / max(len(daily_counts), 1), 2)
            },
            "performance_metrics": {
                "avg_query_time_ms": 15.2,
                "slow_queries_count": 0,
                "connection_pool_usage": 0.45,
                "cache_hit_rate": 0.87
            }
        }
        
        logger.info("Retrieved database statistics", 
                   total_videos=total_videos,
                   total_channels=total_channels,
                   user=current_user["username"])
        
        return stats
        
    except Exception as e:
        logger.error("Failed to get database statistics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve database statistics"
        )


@router.post("/database/export", response_model=Dict[str, Any])
async def export_database_data(
    export_request: Dict[str, Any],
    current_user: Dict = Depends(get_current_user_dependency())
):
    """Export database data in various formats (CSV, JSON)."""
    
    try:
        format_type = export_request.get("format", "csv").lower()
        table = export_request.get("table", "videos")
        filters = export_request.get("filters", {})
        
        if format_type not in ["csv", "json"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid export format. Supported formats: csv, json"
            )
        
        if table not in ["videos", "channels", "statistics"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid table. Supported tables: videos, channels, statistics"
            )
        
        # TODO: Implement actual data export from database
        # Mock export data
        
        if table == "videos":
            export_data = [
                {
                    "id": "dQw4w9WgXcQ",
                    "title": "Sample Video 1",
                    "channel_id": "UCbfYPyITQ-7l4upoX8nvctg",
                    "processed_at": "2024-01-15T10:30:00Z",
                    "cost_estimate": 0.25,
                    "processing_time_seconds": 45.2
                },
                {
                    "id": "dQw4w9WgXcR",
                    "title": "Sample Video 2",
                    "channel_id": "UCbfYPyITQ-7l4upoX8nvctg",
                    "processed_at": "2024-01-14T15:20:00Z",
                    "cost_estimate": 0.28,
                    "processing_time_seconds": 52.1
                }
            ]
        else:
            export_data = []
        
        # Generate export content
        if format_type == "csv":
            import csv
            import io
            
            output = io.StringIO()
            if export_data:
                writer = csv.DictWriter(output, fieldnames=export_data[0].keys())
                writer.writeheader()
                writer.writerows(export_data)
            
            export_content = output.getvalue()
            content_type = "text/csv"
            
        else:  # json
            import json
            export_content = json.dumps(export_data, indent=2)
            content_type = "application/json"
        
        filename = f"{table}_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{format_type}"
        
        logger.info("Exported database data", 
                   table=table,
                   format=format_type,
                   records=len(export_data),
                   user=current_user["username"])
        
        return {
            "export_content": export_content,
            "content_type": content_type,
            "filename": filename,
            "record_count": len(export_data),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to export database data", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export database data"
        )@router.get(
"/channels-overview")
async def get_channels_overview(
    current_user: Dict = Depends(get_current_user_dependency())
):
    """Get overview analytics for all channels."""
    try:
        summary = channel_db_service.get_all_channels_summary()
        
        # Calculate additional metrics
        channels = summary.get("channels", [])
        
        # Channel performance metrics
        channel_metrics = []
        for channel in channels:
            if channel["video_count"] > 0:
                channel_metrics.append({
                    "name": channel["channel_name"],
                    "display_name": channel["display_name"],
                    "video_count": channel["video_count"],
                    "subtitle_count": channel["subtitle_count"],
                    "subtitle_coverage": round((channel["subtitle_count"] / channel["video_count"]) * 100, 1) if channel["video_count"] > 0 else 0,
                    "latest_video": channel["latest_video"],
                    "first_video": channel["first_video"]
                })
        
        # Sort by video count
        channel_metrics.sort(key=lambda x: x["video_count"], reverse=True)
        
        return {
            "overview": {
                "total_channels": summary["total_channels"],
                "total_videos": summary["total_videos"],
                "total_subtitles": summary["total_subtitles"],
                "channels_with_subtitles": summary["channels_with_subtitles"],
                "avg_videos_per_channel": round(summary["total_videos"] / max(summary["total_channels"], 1), 1),
                "subtitle_coverage_rate": round((summary["total_subtitles"] / max(summary["total_videos"], 1)) * 100, 1)
            },
            "channels": channel_metrics,
            "latest_activity": summary["latest_activity"]
        }
        
    except Exception as e:
        logger.error("Failed to get channels overview", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve channels overview"
        )


@router.get("/channel/{channel_name}")
async def get_channel_analytics_detailed(
    channel_name: str,
    days: int = 30,
    current_user: Dict = Depends(get_current_user_dependency())
):
    """Get detailed analytics for a specific channel."""
    try:
        analytics = channel_db_service.get_channel_analytics(channel_name, days)
        
        if not analytics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found or no data available"
            )
        
        return analytics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get channel analytics", 
                    channel=channel_name, 
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve channel analytics"
        )


@router.get("/metrics")
async def get_analytics_metrics(
    timeRange: str = Query("24h", description="Time range for metrics"),
    current_user: Optional[Dict] = Depends(get_optional_user)
):
    """Get analytics metrics for the specified time range."""
    try:
        import sqlite3
        from pathlib import Path
        from datetime import datetime, timedelta
        
        downloads_dir = Path("yt2telegram/downloads")
        
        # Parse time range
        hours = 24
        if timeRange == "1h":
            hours = 1
        elif timeRange == "24h":
            hours = 24
        elif timeRange == "7d":
            hours = 24 * 7
        elif timeRange == "30d":
            hours = 24 * 30
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        cutoff_str = cutoff_time.strftime('%Y-%m-%d %H:%M:%S')
        
        # Initialize metrics
        total_videos = 0
        active_channels = 0
        total_cost_today = 0.0
        total_processing_time = 0.0
        success_count = 0
        videos_last_hour = 0
        
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        hour_ago = datetime.now() - timedelta(hours=1)
        
        if downloads_dir.exists():
            for db_file in downloads_dir.glob("*.db"):
                try:
                    conn = sqlite3.connect(db_file)
                    conn.row_factory = sqlite3.Row
                    
                    active_channels += 1
                    
                    # Get videos in time range
                    cursor = conn.execute("""
                        SELECT 
                            COUNT(*) as count,
                            SUM(CASE WHEN cost_estimate IS NOT NULL THEN cost_estimate ELSE 0 END) as cost,
                            AVG(CASE WHEN processing_time_seconds IS NOT NULL THEN processing_time_seconds ELSE 0 END) as avg_time,
                            SUM(CASE WHEN summary IS NOT NULL AND summary != '' THEN 1 ELSE 0 END) as success
                        FROM videos
                        WHERE processed_at >= ?
                    """, (cutoff_str,))
                    
                    stats = cursor.fetchone()
                    total_videos += stats['count']
                    total_processing_time += (stats['avg_time'] or 0.0) * stats['count']
                    success_count += stats['success']
                    
                    # Get today's cost
                    cursor = conn.execute("""
                        SELECT SUM(CASE WHEN cost_estimate IS NOT NULL THEN cost_estimate ELSE 0 END) as cost
                        FROM videos
                        WHERE DATE(processed_at) = DATE('now')
                    """)
                    today_cost = cursor.fetchone()
                    total_cost_today += today_cost['cost'] or 0.0
                    
                    # Get last hour count
                    cursor = conn.execute("""
                        SELECT COUNT(*) as count
                        FROM videos
                        WHERE processed_at >= datetime('now', '-1 hour')
                    """)
                    videos_last_hour += cursor.fetchone()['count']
                    
                    conn.close()
                    
                except Exception as e:
                    logger.error(f"Error processing database {db_file.name}", error=str(e))
        
        # Calculate metrics
        avg_processing_time = (total_processing_time / total_videos) if total_videos > 0 else 0.0
        success_rate = (success_count / total_videos) if total_videos > 0 else 0.0
        processing_rate = videos_last_hour  # videos per hour
        
        return {
            "overview": {
                "total_videos_processed": total_videos,
                "active_channels": active_channels,
                "processing_queue_size": 0,  # Would need separate queue tracking
                "total_cost_today": round(total_cost_today, 2),
                "avg_processing_time": round(avg_processing_time, 1),
                "success_rate": round(success_rate, 2)
            },
            "real_time": {
                "videos_processed_last_hour": videos_last_hour,
                "current_processing_rate": processing_rate,
                "active_connections": 0,  # Would need WebSocket tracking
                "system_load": 0.35,  # Placeholder
                "memory_usage": 0.68,  # Placeholder
                "disk_usage": 0.42  # Placeholder
            },
            "alerts": []  # Would need alert system
        }
        
    except Exception as e:
        logger.error("Failed to get analytics metrics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analytics metrics"
        )


@router.get("/performance")
async def get_performance_data(
    timeRange: str = Query("24h", description="Time range for performance data"),
    current_user: Optional[Dict] = Depends(get_optional_user)
):
    """Get performance metrics and charts data."""
    try:
        import sqlite3
        from pathlib import Path
        from datetime import datetime, timedelta
        
        downloads_dir = Path("yt2telegram/downloads")
        
        # Parse time range
        hours = 24
        if timeRange == "1h":
            hours = 1
        elif timeRange == "24h":
            hours = 24
        elif timeRange == "7d":
            hours = 24 * 7
        elif timeRange == "30d":
            hours = 24 * 30
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        cutoff_str = cutoff_time.strftime('%Y-%m-%d %H:%M:%S')
        
        processing_times = []
        response_times = []
        throughput_data = []
        
        if downloads_dir.exists():
            for db_file in downloads_dir.glob("*.db"):
                try:
                    conn = sqlite3.connect(db_file)
                    conn.row_factory = sqlite3.Row
                    
                    # Get processing time trends
                    cursor = conn.execute("""
                        SELECT 
                            datetime(processed_at) as timestamp,
                            processing_time_seconds
                        FROM videos
                        WHERE processed_at >= ? AND processing_time_seconds IS NOT NULL
                        ORDER BY processed_at
                    """, (cutoff_str,))
                    
                    for row in cursor.fetchall():
                        processing_times.append({
                            "timestamp": row['timestamp'],
                            "value": row['processing_time_seconds']
                        })
                    
                    conn.close()
                    
                except Exception as e:
                    logger.error(f"Error processing database {db_file.name}", error=str(e))
        
        return {
            "processing_times": processing_times[-100:],  # Last 100 data points
            "response_times": response_times,  # Placeholder
            "throughput": throughput_data,  # Placeholder
            "summary": {
                "avg_processing_time": sum(p["value"] for p in processing_times) / len(processing_times) if processing_times else 0,
                "max_processing_time": max((p["value"] for p in processing_times), default=0),
                "min_processing_time": min((p["value"] for p in processing_times), default=0)
            }
        }
        
    except Exception as e:
        logger.error("Failed to get performance data", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve performance data"
        )


@router.get("/costs")
async def get_cost_data(
    timeRange: str = Query("24h", description="Time range for cost data"),
    current_user: Optional[Dict] = Depends(get_optional_user)
):
    """Get cost analysis data."""
    try:
        import sqlite3
        from pathlib import Path
        from datetime import datetime, timedelta
        
        downloads_dir = Path("yt2telegram/downloads")
        
        # Parse time range
        days = 1
        if timeRange == "1h":
            days = 1
        elif timeRange == "24h":
            days = 1
        elif timeRange == "7d":
            days = 7
        elif timeRange == "30d":
            days = 30
        
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        total_cost = 0.0
        cost_by_model = {}
        cost_by_channel = {}
        daily_costs = {}
        
        if downloads_dir.exists():
            for db_file in downloads_dir.glob("*.db"):
                try:
                    conn = sqlite3.connect(db_file)
                    conn.row_factory = sqlite3.Row
                    
                    channel_name = db_file.stem
                    
                    # Get total cost
                    cursor = conn.execute("""
                        SELECT 
                            SUM(CASE WHEN cost_estimate IS NOT NULL THEN cost_estimate ELSE 0 END) as total_cost
                        FROM videos
                        WHERE DATE(processed_at) >= ?
                    """, (cutoff_date,))
                    
                    channel_cost = cursor.fetchone()['total_cost'] or 0.0
                    total_cost += channel_cost
                    cost_by_channel[channel_name] = round(channel_cost, 2)
                    
                    # Get cost by model
                    cursor = conn.execute("""
                        SELECT 
                            primary_model,
                            SUM(CASE WHEN cost_estimate IS NOT NULL THEN cost_estimate ELSE 0 END) as model_cost
                        FROM videos
                        WHERE DATE(processed_at) >= ? AND primary_model IS NOT NULL
                        GROUP BY primary_model
                    """, (cutoff_date,))
                    
                    for row in cursor.fetchall():
                        model = row['primary_model']
                        if model not in cost_by_model:
                            cost_by_model[model] = 0.0
                        cost_by_model[model] += row['model_cost'] or 0.0
                    
                    # Get daily costs
                    cursor = conn.execute("""
                        SELECT 
                            DATE(processed_at) as date,
                            SUM(CASE WHEN cost_estimate IS NOT NULL THEN cost_estimate ELSE 0 END) as daily_cost
                        FROM videos
                        WHERE DATE(processed_at) >= ?
                        GROUP BY DATE(processed_at)
                        ORDER BY date
                    """, (cutoff_date,))
                    
                    for row in cursor.fetchall():
                        date = row['date']
                        if date not in daily_costs:
                            daily_costs[date] = 0.0
                        daily_costs[date] += row['daily_cost'] or 0.0
                    
                    conn.close()
                    
                except Exception as e:
                    logger.error(f"Error processing database {db_file.name}", error=str(e))
        
        # Format daily costs for chart
        cost_trend = [
            {"date": date, "cost": round(cost, 2)}
            for date, cost in sorted(daily_costs.items())
        ]
        
        return {
            "total_cost": round(total_cost, 2),
            "cost_by_model": {k: round(v, 2) for k, v in cost_by_model.items()},
            "cost_by_channel": cost_by_channel,
            "cost_trend": cost_trend,
            "daily_average": round(total_cost / max(len(daily_costs), 1), 2),
            "projected_monthly": round((total_cost / max(len(daily_costs), 1)) * 30, 2) if daily_costs else 0.0
        }
        
    except Exception as e:
        logger.error("Failed to get cost data", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cost data"
        )


@router.get("/trends")
async def get_processing_trends(
    timeRange: str = Query("7d", description="Time range for trends"),
    current_user: Optional[Dict] = Depends(get_optional_user)
):
    """Get processing trends and patterns."""
    try:
        import sqlite3
        from pathlib import Path
        from datetime import datetime, timedelta
        
        downloads_dir = Path("yt2telegram/downloads")
        
        # Parse time range
        days = 7
        if timeRange == "7d":
            days = 7
        elif timeRange == "30d":
            days = 30
        elif timeRange == "24h":
            days = 1
        
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        daily_stats = {}
        cost_stats = {}
        
        if downloads_dir.exists():
            for db_file in downloads_dir.glob("*.db"):
                try:
                    conn = sqlite3.connect(db_file)
                    conn.row_factory = sqlite3.Row
                    
                    # Get daily trends
                    cursor = conn.execute("""
                        SELECT 
                            DATE(processed_at) as date,
                            COUNT(*) as count,
                            AVG(CASE WHEN processing_time_seconds IS NOT NULL THEN processing_time_seconds ELSE 0 END) as avg_time,
                            SUM(CASE WHEN summary IS NOT NULL AND summary != '' THEN 1 ELSE 0 END) as success_count,
                            SUM(CASE WHEN cost_estimate IS NOT NULL THEN cost_estimate ELSE 0 END) as total_cost,
                            SUM(CASE WHEN summarization_method = 'multi' OR summarization_method = 'multi_model' THEN 1 ELSE 0 END) as multi_count
                        FROM videos
                        WHERE DATE(processed_at) >= ?
                        GROUP BY DATE(processed_at)
                        ORDER BY date
                    """, (cutoff_date,))
                    
                    for row in cursor.fetchall():
                        date = row['date']
                        if date not in daily_stats:
                            daily_stats[date] = {
                                "count": 0, "avg_time": 0.0, "success_count": 0, 
                                "total_count": 0, "total_cost": 0.0, "multi_count": 0
                            }
                        daily_stats[date]["count"] += row['count']
                        daily_stats[date]["avg_time"] += row['avg_time'] * row['count']
                        daily_stats[date]["success_count"] += row['success_count']
                        daily_stats[date]["total_count"] += row['count']
                        daily_stats[date]["total_cost"] += row['total_cost'] or 0.0
                        daily_stats[date]["multi_count"] += row['multi_count']
                    
                    conn.close()
                    
                except Exception as e:
                    logger.error(f"Error processing database {db_file.name}", error=str(e))
        
        # Prepare data arrays
        timestamps = []
        volume_values = []
        success_values = []
        avg_times = []
        p95_times = []
        daily_costs = []
        cost_per_video = []
        single_model_counts = []
        multi_model_counts = []
        
        for date, stats in sorted(daily_stats.items()):
            timestamps.append(date)
            volume_values.append(stats["count"])
            
            success_rate = stats["success_count"] / stats["total_count"] if stats["total_count"] > 0 else 0
            success_values.append(round(success_rate, 2))
            
            avg_time = stats["avg_time"] / stats["total_count"] if stats["total_count"] > 0 else 0
            avg_times.append(round(avg_time, 1))
            p95_times.append(round(avg_time * 1.5, 1))  # Estimate
            
            daily_costs.append(round(stats["total_cost"], 2))
            cost_per_vid = stats["total_cost"] / stats["count"] if stats["count"] > 0 else 0
            cost_per_video.append(round(cost_per_vid, 4))
            
            single_model_counts.append(stats["count"] - stats["multi_count"])
            multi_model_counts.append(stats["multi_count"])
        
        # Calculate trends
        total_videos = sum(volume_values)
        avg_success = sum(success_values) / len(success_values) if success_values else 0
        multi_adoption = sum(multi_model_counts) / total_videos if total_videos > 0 else 0
        
        return {
            "processing_volume": {
                "timestamps": timestamps,
                "values": volume_values,
                "trend": "stable",
                "growth_rate": 0.0
            },
            "success_rates": {
                "timestamps": timestamps,
                "values": success_values,
                "avg_success_rate": round(avg_success, 2),
                "trend": "stable"
            },
            "model_adoption": {
                "timestamps": timestamps,
                "single_model": single_model_counts,
                "multi_model": multi_model_counts,
                "multi_model_adoption_rate": round(multi_adoption, 2)
            },
            "processing_times": {
                "timestamps": timestamps,
                "avg_times": avg_times,
                "p95_times": p95_times,
                "trend": "stable"
            },
            "cost_trends": {
                "timestamps": timestamps,
                "daily_costs": daily_costs,
                "cost_per_video": cost_per_video,
                "efficiency_trend": "stable"
            },
            "predictions": {
                "next_week_volume": round(sum(volume_values) / max(len(volume_values), 1) * 7, 0),
                "next_week_cost": round(sum(daily_costs) / max(len(daily_costs), 1) * 7, 2),
                "capacity_utilization": 0.45,
                "bottlenecks": []
            }
        }
        
    except Exception as e:
        logger.error("Failed to get processing trends", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve processing trends"
        )


@router.get("/system-metrics")
async def get_system_metrics(
    current_user: Dict = Depends(get_current_user_dependency())
):
    """Get system-wide metrics and performance data."""
    try:
        summary = channel_db_service.get_all_channels_summary()
        
        # Calculate system metrics
        total_content_size = 0
        processing_stats = {
            "channels_processed": summary["total_channels"],
            "videos_processed": summary["total_videos"],
            "subtitles_extracted": summary["total_subtitles"],
            "processing_success_rate": 95.2,  # Placeholder
            "avg_processing_time": 45.3,  # Placeholder in seconds
            "storage_used_mb": 1250.7  # Placeholder
        }
        
        # Performance trends (placeholder data based on real structure)
        performance_trends = []
        from datetime import datetime, timedelta
        
        for i in range(7):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            performance_trends.append({
                "date": date,
                "videos_processed": max(0, 15 - i * 2),
                "processing_time_avg": 45 + (i * 2),
                "success_rate": max(90, 98 - i)
            })
        
        performance_trends.reverse()
        
        return {
            "processing_stats": processing_stats,
            "performance_trends": performance_trends,
            "resource_usage": {
                "cpu_usage": 23.5,
                "memory_usage": 67.2,
                "disk_usage": 45.8,
                "network_io": 12.3
            },
            "error_rates": {
                "download_errors": 2.1,
                "processing_errors": 1.8,
                "api_errors": 0.5
            }
        }
        
    except Exception as e:
        logger.error("Failed to get system metrics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system metrics"
        )