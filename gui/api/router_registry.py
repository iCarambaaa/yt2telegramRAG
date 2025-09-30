"""
API Router Registry for centralized router management.

CRITICAL: Centralized API endpoint management
"""

from fastapi import APIRouter, Depends
from typing import Dict, List, Any, Optional
from datetime import datetime

from api.versioning import version_manager, get_api_version, require_feature
from api.routers.auth import get_current_user_dependency, require_permission
from utils.logging_config import setup_logging

logger = setup_logging(__name__)


class RouterRegistry:
    """
    Centralized registry for API routers with versioning support.
    
    CRITICAL: API endpoint organization and management
    """
    
    def __init__(self):
        self.routers: Dict[str, Dict[str, APIRouter]] = {}
        self.router_metadata: Dict[str, Dict[str, Any]] = {}
        self.registered_endpoints: List[Dict[str, Any]] = []
    
    def register_router(self, name: str, router: APIRouter, version: str = "1.0", 
                       metadata: Optional[Dict[str, Any]] = None):
        """Register a router with version and metadata."""
        if name not in self.routers:
            self.routers[name] = {}
            self.router_metadata[name] = {}
        
        self.routers[name][version] = router
        self.router_metadata[name][version] = metadata or {}
        
        # Extract endpoint information
        for route in router.routes:
            if hasattr(route, 'methods') and hasattr(route, 'path'):
                for method in route.methods:
                    self.registered_endpoints.append({
                        "router": name,
                        "version": version,
                        "method": method,
                        "path": route.path,
                        "name": getattr(route, 'name', 'unknown'),
                        "tags": getattr(route, 'tags', [])
                    })
        
        logger.info("Router registered", 
                   name=name, 
                   version=version, 
                   endpoints=len([r for r in router.routes if hasattr(r, 'methods')]))
    
    def get_router(self, name: str, version: str = "1.0") -> Optional[APIRouter]:
        """Get router by name and version."""
        return self.routers.get(name, {}).get(version)
    
    def get_available_versions(self, router_name: str) -> List[str]:
        """Get available versions for a router."""
        return list(self.routers.get(router_name, {}).keys())
    
    def get_registry_info(self) -> Dict[str, Any]:
        """Get comprehensive registry information."""
        return {
            "routers": {
                name: {
                    "versions": list(versions.keys()),
                    "metadata": self.router_metadata.get(name, {})
                }
                for name, versions in self.routers.items()
            },
            "total_routers": len(self.routers),
            "total_endpoints": len(self.registered_endpoints),
            "endpoints_by_version": self._group_endpoints_by_version(),
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def _group_endpoints_by_version(self) -> Dict[str, int]:
        """Group endpoints by version."""
        version_counts = {}
        for endpoint in self.registered_endpoints:
            version = endpoint["version"]
            version_counts[version] = version_counts.get(version, 0) + 1
        return version_counts
    
    def create_versioned_app_routers(self, app) -> Dict[str, APIRouter]:
        """Create and register all versioned routers with the app."""
        app_routers = {}
        
        # Create version-specific main routers
        for version in version_manager.supported_versions:
            version_router = APIRouter(prefix=f"/api/v{version}")
            app_routers[version] = version_router
            
            # Add routers for this version
            for router_name, router_versions in self.routers.items():
                if version in router_versions:
                    router = router_versions[version]
                    
                    # Determine prefix based on router name
                    prefix_map = {
                        "auth": "/auth",
                        "channels": "/channels", 
                        "messages": "/messages",
                        "qna": "/qna",
                        "analytics": "/analytics",
                        "system": "/system",
                        "telegram": ""  # No prefix since router already has /webhook/telegram
                    }
                    
                    prefix = prefix_map.get(router_name, f"/{router_name}")
                    
                    version_router.include_router(
                        router, 
                        prefix=prefix,
                        tags=[router_name, f"v{version}"]
                    )
            
            # Register version router with app
            app.include_router(version_router)
            
            logger.info("Version router created", 
                       version=version,
                       included_routers=len([r for r in self.routers.keys() if version in self.routers[r]]))
        
        return app_routers


# Global router registry
router_registry = RouterRegistry()


def create_enhanced_routers():
    """Create enhanced routers with proper dependencies and versioning."""
    
    # Import routers
    from api.routers import auth, channels, messages, qna, analytics, system, telegram_webhook
    
    # Register v1.0 routers (existing functionality)
    router_registry.register_router("auth", auth.router, "1.0", {
        "description": "Authentication and authorization",
        "features": ["jwt_auth", "session_management"]
    })
    
    router_registry.register_router("channels", channels.router, "1.0", {
        "description": "Channel management",
        "features": ["channel_crud", "configuration_management"]
    })
    
    router_registry.register_router("messages", messages.router, "1.0", {
        "description": "Message mirror and Telegram integration", 
        "features": ["message_history", "telegram_sync"]
    })
    
    router_registry.register_router("qna", qna.router, "1.0", {
        "description": "Question and answer system",
        "features": ["basic_qna", "conversation_history"]
    })
    
    router_registry.register_router("analytics", analytics.router, "1.0", {
        "description": "Analytics and statistics",
        "features": ["basic_analytics", "channel_stats"]
    })
    
    router_registry.register_router("system", system.router, "1.0", {
        "description": "System management and monitoring",
        "features": ["system_status", "configuration"]
    })
    
    router_registry.register_router("telegram", telegram_webhook.router, "1.0", {
        "description": "Telegram webhook and bidirectional communication",
        "features": ["webhook_handling", "message_queue", "multi_chat_support"]
    })
    
    # Create v1.1 routers with enhanced features
    _create_v1_1_routers()
    
    return router_registry


def _create_v1_1_routers():
    """Create v1.1 routers with enhanced features."""
    
    # Enhanced QnA router with AI features
    qna_v1_1 = APIRouter()
    
    @qna_v1_1.post("/ask-ai", dependencies=[Depends(require_feature("ai_enhanced"))])
    async def ask_ai_enhanced_question(
        question_data: dict,
        api_version: str = Depends(get_api_version),
        current_user: dict = Depends(get_current_user_dependency())
    ):
        """Enhanced AI-powered question answering (v1.1 only)."""
        return {
            "message": "AI-enhanced QnA feature",
            "version": api_version,
            "features": ["rag_search", "context_awareness", "follow_up_suggestions"]
        }
    
    @qna_v1_1.get("/conversations/ai-summary", dependencies=[Depends(require_feature("ai_enhanced"))])
    async def get_ai_conversation_summary(
        conversation_id: str,
        api_version: str = Depends(get_api_version),
        current_user: dict = Depends(get_current_user_dependency())
    ):
        """Get AI-generated conversation summary (v1.1 only)."""
        return {
            "conversation_id": conversation_id,
            "ai_summary": "AI-generated conversation summary",
            "version": api_version
        }
    
    router_registry.register_router("qna", qna_v1_1, "1.1", {
        "description": "Enhanced QnA with AI capabilities",
        "features": ["ai_enhanced", "rag_search", "conversation_summary"]
    })
    
    # Enhanced Analytics router
    analytics_v1_1 = APIRouter()
    
    @analytics_v1_1.get("/advanced-insights", dependencies=[Depends(require_feature("advanced_analytics"))])
    async def get_advanced_insights(
        api_version: str = Depends(get_api_version),
        current_user: dict = Depends(get_current_user_dependency())
    ):
        """Get advanced AI-powered analytics insights (v1.1 only)."""
        return {
            "insights": ["Advanced analytics feature"],
            "version": api_version,
            "features": ["predictive_analytics", "anomaly_detection"]
        }
    
    @analytics_v1_1.post("/bulk-export", dependencies=[Depends(require_feature("bulk_operations"))])
    async def bulk_export_data(
        export_config: dict,
        api_version: str = Depends(get_api_version),
        current_user: dict = Depends(require_permission("write"))
    ):
        """Bulk data export functionality (v1.1 only)."""
        return {
            "export_id": "bulk_export_123",
            "status": "initiated",
            "version": api_version
        }
    
    router_registry.register_router("analytics", analytics_v1_1, "1.1", {
        "description": "Advanced analytics with AI insights",
        "features": ["advanced_analytics", "bulk_operations", "predictive_insights"]
    })


# Registry information endpoint
registry_router = APIRouter(prefix="/api")


@registry_router.get("/registry")
async def get_router_registry_info():
    """Get API router registry information."""
    return router_registry.get_registry_info()


@registry_router.get("/endpoints")
async def list_all_endpoints():
    """List all registered API endpoints."""
    return {
        "endpoints": router_registry.registered_endpoints,
        "total_count": len(router_registry.registered_endpoints),
        "grouped_by_router": _group_endpoints_by_router(),
        "grouped_by_version": router_registry._group_endpoints_by_version()
    }


def _group_endpoints_by_router() -> Dict[str, int]:
    """Group endpoints by router name."""
    router_counts = {}
    for endpoint in router_registry.registered_endpoints:
        router = endpoint["router"]
        router_counts[router] = router_counts.get(router, 0) + 1
    return router_counts