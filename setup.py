#!/usr/bin/env python3
"""
Setup script for YouTube to Telegram Channel Manager
"""

import os
import shutil
from pathlib import Path

def setup():
    """Setup the project for first use"""
    print("🚀 Setting up YouTube to Telegram Channel Manager...")
    
    # Create .env from example if it doesn't exist
    if not os.path.exists('.env'):
        if os.path.exists('.env.example'):
            shutil.copy('.env.example', '.env')
            print("✅ Created .env from .env.example")
            print("   Please edit .env with your API keys and tokens")
        else:
            print("❌ .env.example not found")
    else:
        print("✅ .env already exists")
    
    # Create COOKIES_FILE from example if it doesn't exist
    if not os.path.exists('COOKIES_FILE'):
        if os.path.exists('COOKIES_FILE.example'):
            shutil.copy('COOKIES_FILE.example', 'COOKIES_FILE')
            print("✅ Created COOKIES_FILE from COOKIES_FILE.example")
            print("   Please add your YouTube cookies to COOKIES_FILE")
        else:
            print("❌ COOKIES_FILE.example not found")
    else:
        print("✅ COOKIES_FILE already exists")
    
    # Create downloads directory
    downloads_dir = Path("yt2telegram/downloads")
    downloads_dir.mkdir(parents=True, exist_ok=True)
    print("✅ Created downloads directory")
    
    print("\n🎉 Setup complete!")
    print("\nNext steps:")
    print("1. Edit .env with your API keys and tokens")
    print("2. Add your YouTube cookies to COOKIES_FILE")
    print("3. Configure your channels in yt2telegram/channels/")
    print("4. Run: python run.py")

if __name__ == "__main__":
    setup()