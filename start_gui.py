#!/usr/bin/env python3
"""Start both backend and frontend servers for the GUI."""

import subprocess
import sys
import time
import requests
import os
import signal
from pathlib import Path

def kill_existing_servers():
    """Kill any existing servers."""
    print("🔄 Stopping any existing servers...")
    try:
        # Kill Python processes (backend)
        subprocess.run(["taskkill", "/F", "/IM", "python.exe"], 
                      capture_output=True, text=True)
        # Kill Node processes (frontend)
        subprocess.run(["taskkill", "/F", "/IM", "node.exe"], 
                      capture_output=True, text=True)
        time.sleep(2)
    except Exception as e:
        print(f"Note: {e}")

def start_backend():
    """Start the backend server."""
    print("🚀 Starting backend server...")
    
    # Change to gui directory and start server
    backend_process = subprocess.Popen([
        sys.executable, "minimal_server.py"
    ], cwd=".", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    # Wait for backend to start
    for i in range(10):
        try:
            response = requests.get("http://127.0.0.1:8000/", timeout=2)
            if response.status_code == 200:
                print("✅ Backend server started successfully")
                
                # Test database endpoint
                try:
                    db_response = requests.get("http://127.0.0.1:8000/api/database/channels", timeout=2)
                    if db_response.status_code == 200:
                        data = db_response.json()
                        print(f"✅ Database API working - Found {data.get('total', 0)} channels")
                    else:
                        print(f"⚠️ Database API returned: {db_response.status_code}")
                except Exception as e:
                    print(f"⚠️ Database API test failed: {e}")
                
                return backend_process
        except requests.exceptions.RequestException:
            time.sleep(1)
    
    print("❌ Backend server failed to start")
    return None

def start_frontend():
    """Start the frontend server."""
    print("🌐 Starting frontend server...")
    
    frontend_dir = Path("gui/web")
    if not frontend_dir.exists():
        print("❌ Frontend directory not found")
        return None
    
    # Check if node_modules exists
    if not (frontend_dir / "node_modules").exists():
        print("📦 Installing frontend dependencies...")
        install_process = subprocess.run([
            "npm", "install"
        ], cwd=frontend_dir, capture_output=True, text=True)
        
        if install_process.returncode != 0:
            print(f"❌ Failed to install dependencies: {install_process.stderr}")
            return None
        print("✅ Dependencies installed")
    
    # Start the frontend
    frontend_process = subprocess.Popen([
        "npm", "run", "dev"
    ], cwd=frontend_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    # Wait for frontend to start
    for i in range(15):
        try:
            response = requests.get("http://localhost:3000", timeout=2)
            if response.status_code == 200:
                print("✅ Frontend server started successfully")
                return frontend_process
        except requests.exceptions.RequestException:
            time.sleep(2)
    
    print("⚠️ Frontend server may still be starting...")
    return frontend_process

def main():
    """Main startup function."""
    print("🎯 Starting Unified GUI Platform...")
    print("=" * 50)
    
    # Kill existing servers
    kill_existing_servers()
    
    # Start backend
    backend_process = start_backend()
    if not backend_process:
        print("❌ Failed to start backend server")
        return
    
    # Start frontend
    frontend_process = start_frontend()
    if not frontend_process:
        print("❌ Failed to start frontend server")
        backend_process.terminate()
        return
    
    print("\n🎉 GUI Platform Started Successfully!")
    print("=" * 50)
    print("🌐 Frontend: http://localhost:3000")
    print("🔧 Backend API: http://127.0.0.1:8000")
    print("📚 API Docs: http://127.0.0.1:8000/docs")
    print("💾 Database API: http://127.0.0.1:8000/api/database/channels")
    print("=" * 50)
    print("Press Ctrl+C to stop both servers")
    
    try:
        # Keep both processes running
        while True:
            # Check if processes are still alive
            if backend_process.poll() is not None:
                print("❌ Backend server stopped unexpectedly")
                break
            if frontend_process.poll() is not None:
                print("❌ Frontend server stopped unexpectedly")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Shutting down servers...")
        
        # Terminate processes
        try:
            backend_process.terminate()
            frontend_process.terminate()
            
            # Wait for graceful shutdown
            time.sleep(2)
            
            # Force kill if needed
            try:
                backend_process.kill()
                frontend_process.kill()
            except:
                pass
                
        except Exception as e:
            print(f"Note during shutdown: {e}")
        
        # Final cleanup
        kill_existing_servers()
        print("✅ Servers stopped")

if __name__ == "__main__":
    main()