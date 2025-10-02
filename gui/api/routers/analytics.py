"""
Analytics and statistics API endpoints.

CRITICAL: System metrics and data visualization
DEPENDENCIES: Database manager, existing analytics
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from .auth import get_current_user_dependency
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


@router.get("/channels", response_model=List[ChannelStatsResponse])
async def get_channel_statistics(
    current_user: Dict = Depends(get_current_user_dependency())
):
    """Get statistics for all channels."""
    
    try:
        # TODO: Query actual channel statistics from database
        # Placeholder implementation
        
        channel_stats = [
            ChannelStatsResponse(
                channel_id="UC123456789",
                channel_name="twominutepapers",
                video_count=15,
                total_processing_time=1875.0,
                average_cost=0.35,
                last_processed=datetime.utcnow().isoformat(),
                success_rate=0.97
            ),
            ChannelStatsResponse(
                channel_id="UC987654321",
                channel_name="isaac_arthur",
                video_count=8,
                total_processing_time=2400.0,
                average_cost=0.42,
                last_processed=(datetime.utcnow() - timedelta(hours=2)).isoformat(),
                success_rate=0.92
            )
        ]
        
        logger.info("Retrieved channel statistics", 
                   channels=len(channel_stats),
                   user=current_user["username"])
        
        return channel_stats
        
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
        # TODO: Integrate with actual database service
        # For now, generate mock data based on filters
        
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Generate mock video records
        mock_videos = []
        total_count = 150  # Mock total
        
        for i in range(min(page_size, total_count - offset)):
            video_id = f"video_{offset + i + 1:03d}"
            mock_videos.append({
                "id": f"dQw4w9WgXc{video_id[-1]}",
                "title": f"Sample Video Title {offset + i + 1}",
                "channel_id": channel_id or "UCbfYPyITQ-7l4upoX8nvctg",
                "published_at": "2024-01-15",
                "processed_at": "2024-01-15T10:30:00Z",
                "summarization_method": "multi" if (offset + i) % 3 == 0 else "single",
                "primary_model": "gpt-4o-mini",
                "secondary_model": "claude-3-haiku" if (offset + i) % 3 == 0 else None,
                "synthesis_model": "gpt-4o" if (offset + i) % 3 == 0 else None,
                "processing_time_seconds": 45.2 + (i * 2.1),
                "cost_estimate": 0.25 + (i * 0.02),
                "token_usage": {
                    "input_tokens": 2500 + (i * 100),
                    "output_tokens": 800 + (i * 50),
                    "total_tokens": 3300 + (i * 150)
                },
                "has_summary": True,
                "summary_length": 245 + (i * 10),
                "fallback_used": (offset + i) % 10 == 0
            })
        
        # Apply search filter to mock data
        if search:
            mock_videos = [v for v in mock_videos if search.lower() in v["title"].lower()]
            total_count = len(mock_videos)
        
        # Apply other filters
        if has_summary is not None:
            mock_videos = [v for v in mock_videos if v["has_summary"] == has_summary]
            total_count = len(mock_videos)
        
        if summarization_method:
            mock_videos = [v for v in mock_videos if v["summarization_method"] == summarization_method]
            total_count = len(mock_videos)
        
        logger.info("Retrieved video records", 
                   page=page, 
                   page_size=page_size, 
                   total=total_count,
                   user=current_user["username"])
        
        return {
            "videos": mock_videos,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": (total_count + page_size - 1) // page_size,
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
        # TODO: Query actual video from database
        # Mock detailed video data
        
        video_details = {
            "id": video_id,
            "title": "Sample Video Title - Detailed View",
            "channel_id": "UCbfYPyITQ-7l4upoX8nvctg",
            "published_at": "2024-01-15",
            "processed_at": "2024-01-15T10:30:00Z",
            "raw_subtitles": "This is the raw subtitle content extracted from the video...",
            "cleaned_subtitles": "This is the cleaned subtitle content after processing...",
            "summary": "This is the generated summary of the video content...",
            "summarization_method": "multi",
            "primary_summary": "Primary model summary content...",
            "secondary_summary": "Secondary model summary content...",
            "synthesis_summary": "Final synthesized summary content...",
            "primary_model": "gpt-4o-mini",
            "secondary_model": "claude-3-haiku",
            "synthesis_model": "gpt-4o",
            "token_usage_json": '{"primary": {"input": 2500, "output": 800}, "secondary": {"input": 2500, "output": 750}, "synthesis": {"input": 1550, "output": 400}}',
            "processing_time_seconds": 45.2,
            "cost_estimate": 0.28,
            "fallback_used": False,
            "metadata": {
                "duration": "10:23",
                "view_count": 15000,
                "like_count": 1200,
                "comment_count": 89
            }
        }
        
        logger.info("Retrieved video details", video_id=video_id, user=current_user["username"])
        
        return video_details
        
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
        # TODO: Query actual database statistics
        # Mock comprehensive statistics
        
        stats = {
            "overview": {
                "total_videos": 1247,
                "total_channels": 8,
                "processed_today": 12,
                "processing_errors": 3,
                "total_cost": 342.56,
                "avg_processing_time": 42.3
            },
            "by_channel": [
                {
                    "channel_id": "UCbfYPyITQ-7l4upoX8nvctg",
                    "channel_name": "TwoMinutePapers",
                    "video_count": 456,
                    "total_cost": 125.34,
                    "avg_cost_per_video": 0.27,
                    "success_rate": 0.98
                },
                {
                    "channel_id": "UC123456789abcdef",
                    "channel_name": "Example Channel",
                    "video_count": 234,
                    "total_cost": 67.89,
                    "avg_cost_per_video": 0.29,
                    "success_rate": 0.95
                }
            ],
            "by_model": [
                {
                    "model": "gpt-4o-mini",
                    "usage_count": 892,
                    "total_cost": 234.56,
                    "avg_cost": 0.26,
                    "avg_processing_time": 38.2
                },
                {
                    "model": "multi-model",
                    "usage_count": 355,
                    "total_cost": 108.00,
                    "avg_cost": 0.30,
                    "avg_processing_time": 52.1
                }
            ],
            "processing_trends": {
                "daily_counts": [
                    {"date": "2024-01-15", "count": 12, "cost": 3.24},
                    {"date": "2024-01-14", "count": 8, "cost": 2.16},
                    {"date": "2024-01-13", "count": 15, "cost": 4.05}
                ],
                "success_rate_trend": [
                    {"date": "2024-01-15", "success_rate": 0.92},
                    {"date": "2024-01-14", "success_rate": 0.95},
                    {"date": "2024-01-13", "success_rate": 0.98}
                ]
            },
            "storage_info": {
                "database_size_mb": 245.7,
                "subtitle_storage_mb": 89.3,
                "summary_storage_mb": 34.2,
                "growth_rate_mb_per_day": 2.1
            },
            "performance_metrics": {
                "avg_query_time_ms": 15.2,
                "slow_queries_count": 3,
                "connection_pool_usage": 0.65,
                "cache_hit_rate": 0.87
            }
        }
        
        logger.info("Retrieved database statistics", user=current_user["username"])
        
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
    current_user: Dict = Depends(require_permission("read"))
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