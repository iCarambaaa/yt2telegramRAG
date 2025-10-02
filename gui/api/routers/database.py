"""
Database browser API endpoints.

CRITICAL: Database access and management functionality
DEPENDENCIES: Channel database service, existing SQLite databases
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

from .auth import get_current_user_dependency
from utils.logging_config import setup_logging
from services.channel_database_service import ChannelDatabaseService

logger = setup_logging(__name__)

router = APIRouter()

# Initialize channel database service
channel_db_service = ChannelDatabaseService()


@router.get("/channels")
async def get_database_channels():
    """Get all available channel databases."""
    try:
        channels = channel_db_service.get_available_channels()
        
        return {
            "channels": channels,
            "total": len(channels)
        }
        
    except Exception as e:
        logger.error("Failed to get database channels", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve database channels"
        )


@router.get("/videos")
async def get_videos(
    channel: Optional[str] = Query(None, description="Filter by channel"),
    limit: int = Query(50, description="Number of videos to return"),
    offset: int = Query(0, description="Offset for pagination"),
    search: Optional[str] = Query(None, description="Search query")
):
    """Get videos from databases with filtering and search."""
    try:
        if channel:
            # Get videos from specific channel
            if search:
                videos = channel_db_service.search_channel_content(channel, search, limit)
                # Convert search results to video format
                videos = [{
                    "video_id": v["video_id"],
                    "title": v["title"],
                    "summary": v["content"] if v["content_type"] == "summary" else "",
                    "upload_date": v["upload_date"],
                    "url": v["url"],
                    "channel_name": channel,
                    "relevance_score": v.get("relevance_score", 0)
                } for v in videos if v["content_type"] == "summary"]
            else:
                videos = channel_db_service.get_channel_videos(channel, limit, offset)
        else:
            # Get videos from all channels
            all_channels = channel_db_service.get_available_channels()
            videos = []
            
            for ch in all_channels[:5]:  # Limit to first 5 channels for performance
                channel_videos = channel_db_service.get_channel_videos(
                    ch["channel_id"], 
                    min(limit // len(all_channels[:5]), 10), 
                    0
                )
                videos.extend(channel_videos)
            
            # Sort by upload date
            videos.sort(key=lambda x: x.get("upload_date", ""), reverse=True)
            videos = videos[:limit]
        
        return {
            "videos": videos,
            "total": len(videos),
            "channel": channel,
            "search": search,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error("Failed to get videos", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve videos"
        )


@router.get("/videos/{video_id}")
async def get_video_details(
    video_id: str,
    channel: str = Query(..., description="Channel name"),
    current_user: Dict = Depends(get_current_user_dependency())
):
    """Get detailed information for a specific video."""
    try:
        video_details = channel_db_service.get_video_details(channel, video_id)
        
        if not video_details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )
        
        return video_details
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get video details", 
                    video_id=video_id, 
                    channel=channel, 
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve video details"
        )


@router.get("/statistics")
async def get_database_statistics():
    """Get database statistics and summary information."""
    try:
        summary = channel_db_service.get_all_channels_summary()
        
        # Calculate additional statistics
        channels = summary.get("channels", [])
        
        # Channel size distribution
        size_distribution = {
            "small": len([ch for ch in channels if ch["video_count"] < 50]),
            "medium": len([ch for ch in channels if 50 <= ch["video_count"] < 200]),
            "large": len([ch for ch in channels if ch["video_count"] >= 200])
        }
        
        # Content type breakdown
        content_stats = {
            "videos_with_summaries": sum(1 for ch in channels if ch["video_count"] > 0),
            "videos_with_subtitles": summary["total_subtitles"],
            "subtitle_coverage": round((summary["total_subtitles"] / max(summary["total_videos"], 1)) * 100, 1)
        }
        
        # Recent activity
        recent_channels = [ch for ch in channels if ch["latest_video"]]
        recent_channels.sort(key=lambda x: x["latest_video"], reverse=True)
        
        return {
            "overview": {
                "total_channels": summary["total_channels"],
                "total_videos": summary["total_videos"],
                "total_subtitles": summary["total_subtitles"],
                "channels_with_subtitles": summary["channels_with_subtitles"]
            },
            "size_distribution": size_distribution,
            "content_stats": content_stats,
            "recent_activity": recent_channels[:5],
            "top_channels": sorted(channels, key=lambda x: x["video_count"], reverse=True)[:10]
        }
        
    except Exception as e:
        logger.error("Failed to get database statistics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve database statistics"
        )


@router.get("/search")
async def search_database(
    query: str = Query(..., description="Search query"),
    channels: Optional[str] = Query(None, description="Comma-separated channel names"),
    limit: int = Query(20, description="Maximum results to return"),
    current_user: Dict = Depends(get_current_user_dependency())
):
    """Search across all databases or specific channels."""
    try:
        if channels:
            channel_list = [ch.strip() for ch in channels.split(",")]
        else:
            # Search all available channels
            all_channels = channel_db_service.get_available_channels()
            channel_list = [ch["channel_id"] for ch in all_channels]
        
        # Search across specified channels
        all_results = []
        for channel in channel_list:
            try:
                results = channel_db_service.search_channel_content(channel, query, limit // len(channel_list))
                for result in results:
                    result["channel"] = channel
                all_results.extend(results)
            except Exception as e:
                logger.warning(f"Failed to search channel {channel}", error=str(e))
        
        # Sort by relevance score
        all_results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        return {
            "results": all_results[:limit],
            "query": query,
            "channels_searched": channel_list,
            "total_results": len(all_results)
        }
        
    except Exception as e:
        logger.error("Failed to search database", query=query, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search database"
        )


@router.get("/export")
async def export_data(
    channel: str = Query(..., description="Channel to export"),
    format: str = Query("json", description="Export format (json, csv)"),
    include_subtitles: bool = Query(False, description="Include subtitle data"),
    current_user: Dict = Depends(get_current_user_dependency())
):
    """Export channel data in various formats."""
    try:
        # Get channel videos
        videos = channel_db_service.get_channel_videos(channel, limit=1000)
        
        if not videos:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found or no data available"
            )
        
        # Add subtitle data if requested
        if include_subtitles:
            for video in videos:
                video_details = channel_db_service.get_video_details(channel, video["video_id"])
                if video_details:
                    video["subtitles"] = video_details.get("subtitles", [])
        
        export_data = {
            "channel": channel,
            "exported_at": datetime.utcnow().isoformat(),
            "total_videos": len(videos),
            "include_subtitles": include_subtitles,
            "videos": videos
        }
        
        if format.lower() == "csv":
            # For CSV, we'll return a simplified structure
            # In a real implementation, you'd convert to CSV format
            return {
                "message": "CSV export not yet implemented",
                "data": export_data
            }
        else:
            return export_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to export data", 
                    channel=channel, 
                    format=format, 
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export data"
        )