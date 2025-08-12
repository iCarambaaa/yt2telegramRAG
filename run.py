#!/usr/bin/env python3
"""
Entry point for the YouTube to Telegram Channel Manager
"""

import sys
from pathlib import Path

# Add yt2telegram to Python path
sys.path.insert(0, str(Path(__file__).parent / "yt2telegram"))

from yt2telegram.main import main

if __name__ == "__main__":
    main()