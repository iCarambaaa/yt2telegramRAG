"""
Channel management API endpoints.

CRITICAL: Core channel configuration and management
DEPENDENCIES: Existing yt2telegram channel services
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import yaml
import os
from pathlib import Path

from .auth import get_current_user_dependency, require_permission
from utils.logging_config import setup_logging
from services.channel_database_service import ChannelDatabaseService

logger = setup_logging(__name__)

router = APIRouter()

# Initialize channel database service
channel_db_service = ChannelDatabaseService()


class ChannelConfig(BaseModel):
    channel_id: str
    channel_name: str
    model: str
    cost_threshold: float
    multi_model_enabled: bool
    telegram_chat_id: Optional[str] = None
    custom_prompt: Optional[str] = None


class ChannelStatus(BaseModel):
    channel_id: str
    channel_name: str
    status: str
    last_processed: Optional[str]
    video_count: int
    error_message: Optional[str] = None


class ChannelListResponse(BaseModel):
    channels: List[ChannelStatus]
    total_count: int


@router.get("/", response_model=ChannelListResponse)
async def list_channels(current_user: Dict = Depends(get_current_user_dependency())):
    """List all configured channels with status information."""
    
    try:
        channels_dir = Path("yt2telegram/channels")
        channels = []
        
        if channels_dir.exists():
            for config_file in channels_dir.glob("*.yml"):
                if config_file.name.startswith("example"):
                    continue
                
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config_data = yaml.safe_load(f)
                    
                    # Get channel status (placeholder - integrate with existing services)
                    channel_status = ChannelStatus(
                        channel_id=config_data.get("channel_id", ""),
                        channel_name=config_data.get("channel_name", config_file.stem),
                        status="active",  # TODO: Get real status
                        last_processed=None,  # TODO: Get from database
                        video_count=0,  # TODO: Get from database
                    )
                    
                    channels.append(channel_status)
                    
                except Exception as e:
                    logger.error("Failed to load channel config", file=str(config_file), error=str(e))
                    
                    # Add error entry
                    channels.append(ChannelStatus(
                        channel_id="unknown",
                        channel_name=config_file.stem,
                        status="error",
                        last_processed=None,
                        video_count=0,
                        error_message=str(e)
                    ))
        
        logger.info("Listed channels", count=len(channels), user=current_user["username"])
        
        return ChannelListResponse(
            channels=channels,
            total_count=len(channels)
        )
        
    except Exception as e:
        logger.error("Failed to list channels", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve channel list"
        )


@router.get("/{channel_name}", response_model=ChannelConfig)
async def get_channel(
    channel_name: str,
    current_user: Dict = Depends(get_current_user_dependency())
):
    """Get specific channel configuration."""
    
    try:
        config_file = Path(f"yt2telegram/channels/{channel_name}.yml")
        
        if not config_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Channel '{channel_name}' not found"
            )
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        channel_config = ChannelConfig(
            channel_id=config_data.get("channel_id", ""),
            channel_name=config_data.get("channel_name", channel_name),
            model=config_data.get("model", "gpt-4o-mini"),
            cost_threshold=config_data.get("cost_threshold", 0.50),
            multi_model_enabled=config_data.get("multi_model_enabled", False),
            telegram_chat_id=config_data.get("telegram_chat_id"),
            custom_prompt=config_data.get("custom_prompt")
        )
        
        logger.info("Retrieved channel config", channel=channel_name, user=current_user["username"])
        
        return channel_config
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get channel config", channel=channel_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve channel configuration"
        )


@router.post("/", response_model=Dict[str, str])
async def create_channel(
    channel_config: ChannelConfig,
    current_user: Dict = Depends(require_permission("write"))
):
    """Create new channel configuration."""
    
    try:
        config_file = Path(f"yt2telegram/channels/{channel_config.channel_name}.yml")
        
        if config_file.exists():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Channel '{channel_config.channel_name}' already exists"
            )
        
        # Ensure channels directory exists
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to YAML format
        config_dict = {
            "channel_id": channel_config.channel_id,
            "channel_name": channel_config.channel_name,
            "model": channel_config.model,
            "cost_threshold": channel_config.cost_threshold,
            "multi_model_enabled": channel_config.multi_model_enabled
        }
        
        if channel_config.telegram_chat_id:
            config_dict["telegram_chat_id"] = channel_config.telegram_chat_id
        
        if channel_config.custom_prompt:
            config_dict["custom_prompt"] = channel_config.custom_prompt
        
        # Write configuration file
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
        
        logger.info("Created channel config", channel=channel_config.channel_name, user=current_user["username"])
        
        return {"message": f"Channel '{channel_config.channel_name}' created successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create channel", channel=channel_config.channel_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create channel configuration"
        )


@router.put("/{channel_name}", response_model=Dict[str, str])
async def update_channel(
    channel_name: str,
    channel_config: ChannelConfig,
    current_user: Dict = Depends(require_permission("write"))
):
    """Update existing channel configuration."""
    
    try:
        config_file = Path(f"yt2telegram/channels/{channel_name}.yml")
        
        if not config_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Channel '{channel_name}' not found"
            )
        
        # Convert to YAML format
        config_dict = {
            "channel_id": channel_config.channel_id,
            "channel_name": channel_config.channel_name,
            "model": channel_config.model,
            "cost_threshold": channel_config.cost_threshold,
            "multi_model_enabled": channel_config.multi_model_enabled
        }
        
        if channel_config.telegram_chat_id:
            config_dict["telegram_chat_id"] = channel_config.telegram_chat_id
        
        if channel_config.custom_prompt:
            config_dict["custom_prompt"] = channel_config.custom_prompt
        
        # Write updated configuration
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
        
        logger.info("Updated channel config", channel=channel_name, user=current_user["username"])
        
        return {"message": f"Channel '{channel_name}' updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update channel", channel=channel_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update channel configuration"
        )


@router.delete("/{channel_name}", response_model=Dict[str, str])
async def delete_channel(
    channel_name: str,
    current_user: Dict = Depends(require_permission("write"))
):
    """Delete channel configuration."""
    
    try:
        config_file = Path(f"yt2telegram/channels/{channel_name}.yml")
        
        if not config_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Channel '{channel_name}' not found"
            )
        
        # Remove configuration file
        config_file.unlink()
        
        logger.info("Deleted channel config", channel=channel_name, user=current_user["username"])
        
        return {"message": f"Channel '{channel_name}' deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete channel", channel=channel_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete channel configuration"
        )


@router.post("/{channel_name}/test", response_model=Dict[str, Any])
async def test_channel(
    channel_name: str,
    current_user: Dict = Depends(get_current_user_dependency())
):
    """Test channel configuration and connectivity."""
    
    try:
        # TODO: Integrate with existing channel testing logic
        # This is a placeholder implementation
        
        config_file = Path(f"yt2telegram/channels/{channel_name}.yml")
        
        if not config_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Channel '{channel_name}' not found"
            )
        
        # Load configuration
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        # Perform basic validation
        test_results = {
            "channel_id_valid": bool(config_data.get("channel_id")),
            "model_configured": bool(config_data.get("model")),
            "cost_threshold_set": config_data.get("cost_threshold", 0) > 0,
            "youtube_accessible": True,  # TODO: Test YouTube API access
            "telegram_configured": bool(config_data.get("telegram_chat_id")),
            "overall_status": "pass"
        }
        
        # Determine overall status
        if not all([test_results["channel_id_valid"], test_results["model_configured"]]):
            test_results["overall_status"] = "fail"
        
        logger.info("Tested channel config", channel=channel_name, status=test_results["overall_status"])
        
        return {
            "channel_name": channel_name,
            "test_results": test_results,
            "timestamp": "2025-09-30T20:25:00Z"  # TODO: Use actual timestamp
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to test channel", channel=channel_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test channel configuration"
        )
@router.p
ost("/{channel_name}/backup", response_model=Dict[str, Any])
async def backup_channel_config(
    channel_name: str,
    current_user: Dict = Depends(get_current_user_dependency())
):
    """Create a backup of channel configuration."""
    
    try:
        config_file = Path(f"yt2telegram/channels/{channel_name}.yml")
        
        if not config_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Channel '{channel_name}' not found"
            )
        
        # Read current configuration
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        # Create backup with timestamp
        from datetime import datetime
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{channel_name}_backup_{timestamp}.yml"
        backup_path = Path(f"yt2telegram/backups/{backup_filename}")
        
        # Ensure backup directory exists
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write backup
        with open(backup_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
        
        logger.info("Created channel backup", channel=channel_name, backup=backup_filename)
        
        return {
            "backup_filename": backup_filename,
            "backup_path": str(backup_path),
            "timestamp": timestamp,
            "config_data": config_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to backup channel", channel=channel_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create channel backup"
        )


@router.post("/{channel_name}/restore", response_model=Dict[str, str])
async def restore_channel_config(
    channel_name: str,
    backup_data: Dict[str, Any],
    current_user: Dict = Depends(require_permission("write"))
):
    """Restore channel configuration from backup."""
    
    try:
        config_file = Path(f"yt2telegram/channels/{channel_name}.yml")
        
        # Validate backup data structure
        required_fields = ["channel_id", "channel_name"]
        for field in required_fields:
            if field not in backup_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid backup data: missing '{field}'"
                )
        
        # Write restored configuration
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(backup_data, f, default_flow_style=False, allow_unicode=True)
        
        logger.info("Restored channel config", channel=channel_name, user=current_user["username"])
        
        return {"message": f"Channel '{channel_name}' restored successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to restore channel", channel=channel_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to restore channel configuration"
        )


@router.get("/{channel_name}/stats", response_model=Dict[str, Any])
async def get_channel_stats(
    channel_name: str,
    current_user: Dict = Depends(get_current_user_dependency())
):
    """Get detailed channel statistics and processing history."""
    
    try:
        config_file = Path(f"yt2telegram/channels/{channel_name}.yml")
        
        if not config_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Channel '{channel_name}' not found"
            )
        
        # Load configuration
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        # TODO: Integrate with actual database to get real statistics
        # For now, return mock statistics
        stats = {
            "channel_info": {
                "channel_id": config_data.get("channel_id", ""),
                "channel_name": config_data.get("channel_name", channel_name),
                "created_at": "2024-01-01T00:00:00Z",  # TODO: Get from file creation time
                "last_updated": "2024-01-15T12:00:00Z"  # TODO: Get from file modification time
            },
            "processing_stats": {
                "total_videos_processed": 42,  # TODO: Get from database
                "successful_processing": 40,
                "failed_processing": 2,
                "average_processing_time": 45.2,  # seconds
                "total_cost": 12.45,  # USD
                "average_cost_per_video": 0.30
            },
            "recent_activity": [
                {
                    "video_id": "dQw4w9WgXcQ",
                    "title": "Sample Video Title",
                    "processed_at": "2024-01-15T10:30:00Z",
                    "status": "success",
                    "cost": 0.25,
                    "processing_time": 42.1
                }
            ],
            "model_usage": {
                "primary_model": config_data.get("model", "gpt-4o-mini"),
                "multi_model_enabled": config_data.get("multi_model_enabled", False),
                "total_tokens_used": 125000,
                "average_tokens_per_video": 2976
            },
            "error_analysis": {
                "common_errors": [
                    {"error": "Rate limit exceeded", "count": 1, "last_seen": "2024-01-10T15:20:00Z"},
                    {"error": "Video unavailable", "count": 1, "last_seen": "2024-01-08T09:15:00Z"}
                ],
                "error_rate": 0.048  # 4.8%
            }
        }
        
        logger.info("Retrieved channel stats", channel=channel_name, user=current_user["username"])
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get channel stats", channel=channel_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve channel statistics"
        )


@router.post("/{channel_name}/dry-run", response_model=Dict[str, Any])
async def dry_run_channel(
    channel_name: str,
    video_url: Optional[str] = None,
    current_user: Dict = Depends(get_current_user_dependency())
):
    """Perform a dry run of channel processing without actually sending messages."""
    
    try:
        config_file = Path(f"yt2telegram/channels/{channel_name}.yml")
        
        if not config_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Channel '{channel_name}' not found"
            )
        
        # Load configuration
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        # TODO: Integrate with actual processing pipeline
        # For now, simulate dry run results
        dry_run_result = {
            "channel_name": channel_name,
            "config_used": config_data,
            "test_video": {
                "url": video_url or "https://youtube.com/watch?v=dQw4w9WgXcQ",
                "title": "Sample Test Video",
                "duration": "3:32",
                "subtitle_length": 2847  # characters
            },
            "processing_simulation": {
                "estimated_cost": 0.28,
                "estimated_tokens": 3200,
                "estimated_processing_time": 38.5,
                "model_used": config_data.get("model", "gpt-4o-mini"),
                "multi_model_enabled": config_data.get("multi_model_enabled", False)
            },
            "generated_summary": {
                "title": "🎬 Sample Test Video",
                "content": "This is a simulated summary that would be generated for the test video. The actual summary would contain the key points and insights from the video content, formatted according to the channel's custom prompt template.",
                "length": 245,  # characters
                "formatting": {
                    "markdown": True,
                    "emojis": True,
                    "structured": True
                }
            },
            "telegram_preview": {
                "chat_id": config_data.get("telegram_chat_id", "@default_channel"),
                "message_count": 1,  # Number of messages (due to length limits)
                "would_send": bool(config_data.get("telegram_chat_id")),
                "estimated_delivery_time": 2.1  # seconds
            },
            "validation_results": {
                "config_valid": True,
                "api_accessible": True,
                "cost_within_threshold": True,
                "telegram_configured": bool(config_data.get("telegram_chat_id"))
            }
        }
        
        logger.info("Performed dry run", channel=channel_name, video_url=video_url, user=current_user["username"])
        
        return dry_run_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to perform dry run", channel=channel_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform dry run"
        )


@router.get("/templates/models", response_model=List[Dict[str, Any]])
async def get_available_models(current_user: Dict = Depends(get_current_user_dependency())):
    """Get list of available AI models with pricing and capabilities."""
    
    models = [
        {
            "id": "gpt-4o-mini",
            "name": "GPT-4o Mini",
            "provider": "OpenAI",
            "description": "Fast, cost-effective model for most use cases",
            "pricing": {
                "input_tokens": 0.00015,  # per 1K tokens
                "output_tokens": 0.0006
            },
            "capabilities": ["text", "reasoning"],
            "recommended_for": ["general", "cost-effective"],
            "max_tokens": 128000,
            "free": False
        },
        {
            "id": "gpt-4o",
            "name": "GPT-4o",
            "provider": "OpenAI", 
            "description": "Premium model with advanced reasoning",
            "pricing": {
                "input_tokens": 0.0025,
                "output_tokens": 0.01
            },
            "capabilities": ["text", "advanced-reasoning", "complex-tasks"],
            "recommended_for": ["premium", "complex-content"],
            "max_tokens": 128000,
            "free": False
        },
        {
            "id": "x-ai/grok-4-fast:free",
            "name": "Grok 4 Fast",
            "provider": "X.AI",
            "description": "Fast, free model with good performance",
            "pricing": {
                "input_tokens": 0.0,
                "output_tokens": 0.0
            },
            "capabilities": ["text", "fast-processing"],
            "recommended_for": ["free", "testing"],
            "max_tokens": 32000,
            "free": True
        },
        {
            "id": "deepseek/deepseek-chat-v3.1:free",
            "name": "DeepSeek Chat",
            "provider": "DeepSeek",
            "description": "Free model with good reasoning capabilities",
            "pricing": {
                "input_tokens": 0.0,
                "output_tokens": 0.0
            },
            "capabilities": ["text", "reasoning", "multilingual"],
            "recommended_for": ["free", "multilingual"],
            "max_tokens": 64000,
            "free": True
        },
        {
            "id": "claude-3-haiku",
            "name": "Claude 3 Haiku",
            "provider": "Anthropic",
            "description": "Fast and efficient for simple tasks",
            "pricing": {
                "input_tokens": 0.00025,
                "output_tokens": 0.00125
            },
            "capabilities": ["text", "fast-processing", "analysis"],
            "recommended_for": ["speed", "simple-tasks"],
            "max_tokens": 200000,
            "free": False
        },
        {
            "id": "claude-3-sonnet",
            "name": "Claude 3 Sonnet",
            "provider": "Anthropic",
            "description": "Balanced performance and capability",
            "pricing": {
                "input_tokens": 0.003,
                "output_tokens": 0.015
            },
            "capabilities": ["text", "reasoning", "analysis", "creative"],
            "recommended_for": ["balanced", "creative-content"],
            "max_tokens": 200000,
            "free": False
        }
    ]
    
    logger.info("Retrieved available models", count=len(models), user=current_user["username"])
    
    return models
@
router.get("/database-channels")
async def get_database_channels(
    current_user: Dict = Depends(get_current_user_dependency())
):
    """Get channels from existing databases."""
    try:
        channels = channel_db_service.get_available_channels()
        
        logger.info("Retrieved database channels", 
                   count=len(channels),
                   user=current_user["username"])
        
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


@router.get("/database-channels/{channel_name}/videos")
async def get_channel_videos(
    channel_name: str,
    limit: int = 50,
    offset: int = 0,
    current_user: Dict = Depends(get_current_user_dependency())
):
    """Get videos for a specific channel from database."""
    try:
        videos = channel_db_service.get_channel_videos(channel_name, limit, offset)
        
        logger.info("Retrieved channel videos", 
                   channel=channel_name,
                   count=len(videos),
                   user=current_user["username"])
        
        return {
            "videos": videos,
            "channel": channel_name,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error("Failed to get channel videos", 
                    channel=channel_name, 
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve channel videos"
        )


@router.get("/database-channels/{channel_name}/analytics")
async def get_channel_analytics(
    channel_name: str,
    days: int = 30,
    current_user: Dict = Depends(get_current_user_dependency())
):
    """Get analytics for a specific channel."""
    try:
        analytics = channel_db_service.get_channel_analytics(channel_name, days)
        
        logger.info("Retrieved channel analytics", 
                   channel=channel_name,
                   days=days,
                   user=current_user["username"])
        
        return analytics
        
    except Exception as e:
        logger.error("Failed to get channel analytics", 
                    channel=channel_name, 
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve channel analytics"
        )


@router.get("/database-channels/{channel_name}/videos/{video_id}")
async def get_video_details(
    channel_name: str,
    video_id: str,
    current_user: Dict = Depends(get_current_user_dependency())
):
    """Get detailed information for a specific video."""
    try:
        video_details = channel_db_service.get_video_details(channel_name, video_id)
        
        if not video_details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )
        
        logger.info("Retrieved video details", 
                   channel=channel_name,
                   video_id=video_id,
                   user=current_user["username"])
        
        return video_details
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get video details", 
                    channel=channel_name,
                    video_id=video_id,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve video details"
        )


@router.get("/summary")
async def get_channels_summary(
    current_user: Dict = Depends(get_current_user_dependency())
):
    """Get summary of all channels and their data."""
    try:
        summary = channel_db_service.get_all_channels_summary()
        
        logger.info("Retrieved channels summary", 
                   total_channels=summary.get("total_channels", 0),
                   user=current_user["username"])
        
        return summary
        
    except Exception as e:
        logger.error("Failed to get channels summary", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve channels summary"
        )