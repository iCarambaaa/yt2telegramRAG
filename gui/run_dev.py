"""
Development server runner for the Unified GUI Platform.

CRITICAL: Development environment setup with hot-reload
"""

import uvicorn
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from gui.config import get_settings
from gui.utils.logging_config import setup_logging

logger = setup_logging(__name__)


def main():
    """Run development server with hot-reload and debugging."""
    
    settings = get_settings()
    
    logger.info("Starting Unified GUI Platform development server")
    logger.info("Configuration", 
               host=settings.host,
               port=settings.port,
               debug=settings.debug,
               log_level=settings.log_level)
    
    # Ensure data directory exists
    os.makedirs("gui/data", exist_ok=True)
    
    # Run development server
    uvicorn.run(
        "gui.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
        access_log=True,
        reload_dirs=["gui/"],
        reload_excludes=["gui/data/", "*.db", "*.log"]
    )


if __name__ == "__main__":
    main()