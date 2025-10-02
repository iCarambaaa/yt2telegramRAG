#!/usr/bin/env python3
"""Restart the server with proper database router."""

import subprocess
import sys
import time
import requests
import os

def kill_existing_server():
    """Kill any existing server on port 8000."""
    try:
        # Try to connect to see if server is running
        response = requests.get("http://127.0.0.1:8000/", timeout=2)
        print("🔄 Server is running, attempting to stop...")
        
        # Kill uvicorn processes on Windows
        subprocess.run(["taskkill", "/F", "/IM", "python.exe"], 
                      capture_output=True, text=True)
        time.sleep(2)
        
    except requests.exceptions.RequestException:
        print("✓ No server running on port 8000")

def start_server():
    """Start the server."""
    print("🚀 Starting server...")
    os.chdir("gui")
    
    # Start the server
    process = subprocess.Popen([
        sys.executable, "run_simple.py"
    ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    # Wait a bit for startup
    time.sleep(3)
    
    # Test if server is responding
    try:
        response = requests.get("http://127.0.0.1:8000/", timeout=5)
        print("✓ Server started successfully")
        
        # Test database endpoint
        try:
            db_response = requests.get("http://127.0.0.1:8000/api/database/channels", timeout=5)
            if db_response.status_code == 200:
                print("✓ Database endpoints working")
                data = db_response.json()
                print(f"  Found {data.get('total', 0)} channels")
            else:
                print(f"⚠ Database endpoint returned: {db_response.status_code}")
        except Exception as e:
            print(f"⚠ Database endpoint test failed: {e}")
            
    except requests.exceptions.RequestException as e:
        print(f"✗ Server failed to start: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🔧 Restarting GUI server...")
    kill_existing_server()
    
    if start_server():
        print("\n🎉 Server restart complete!")
        print("Frontend: http://localhost:3000")
        print("Backend: http://127.0.0.1:8000")
        print("API Docs: http://127.0.0.1:8000/docs")
        print("\nPress Ctrl+C to stop the server")
        
        try:
            # Keep the script running
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Stopping server...")
            kill_existing_server()
    else:
        print("❌ Failed to start server")
        sys.exit(1)