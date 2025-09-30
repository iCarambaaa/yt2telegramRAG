#!/usr/bin/env python3
"""
Development script to run both FastAPI backend and Next.js frontend
"""

import subprocess
import sys
import os
import time
import signal
from pathlib import Path

def run_backend():
    """Run the FastAPI backend"""
    print("Starting FastAPI backend...")
    backend_process = subprocess.Popen(
        [sys.executable, "run_dev.py"],
        cwd=Path(__file__).parent,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )
    return backend_process

def run_frontend():
    """Run the Next.js frontend"""
    print("Starting Next.js frontend...")
    web_dir = Path(__file__).parent / "web"
    
    # Check if node_modules exists, if not install dependencies
    if not (web_dir / "node_modules").exists():
        print("Installing frontend dependencies...")
        subprocess.run(["npm", "install"], cwd=web_dir, check=True)
    
    frontend_process = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=web_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )
    return frontend_process

def main():
    """Main function to run both services"""
    backend_process = None
    frontend_process = None
    
    try:
        # Start backend
        backend_process = run_backend()
        time.sleep(3)  # Give backend time to start
        
        # Start frontend
        frontend_process = run_frontend()
        
        print("\n" + "="*50)
        print("🚀 Development servers started!")
        print("📱 Frontend: http://localhost:3000")
        print("🔧 Backend API: http://localhost:8000")
        print("📚 API Docs: http://localhost:8000/docs")
        print("="*50)
        print("\nPress Ctrl+C to stop both servers")
        
        # Wait for processes
        while True:
            time.sleep(1)
            
            # Check if processes are still running
            if backend_process.poll() is not None:
                print("❌ Backend process stopped")
                break
            if frontend_process.poll() is not None:
                print("❌ Frontend process stopped")
                break
                
    except KeyboardInterrupt:
        print("\n🛑 Stopping development servers...")
        
    finally:
        # Clean up processes
        if backend_process:
            backend_process.terminate()
            try:
                backend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                backend_process.kill()
                
        if frontend_process:
            frontend_process.terminate()
            try:
                frontend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                frontend_process.kill()
        
        print("✅ Development servers stopped")

if __name__ == "__main__":
    main()