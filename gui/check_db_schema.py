#!/usr/bin/env python3
"""Check the actual database schema."""

import sqlite3
import os

def check_database_schema(db_path):
    """Check the schema of a database."""
    print(f"\n🔍 Checking schema for: {db_path}")
    
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get table names
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row['name'] for row in cursor.fetchall()]
            print(f"📋 Tables: {tables}")
            
            # Check videos table schema
            if 'videos' in tables:
                cursor = conn.execute("PRAGMA table_info(videos)")
                columns = cursor.fetchall()
                print(f"📊 Videos table columns:")
                for col in columns:
                    print(f"   - {col['name']} ({col['type']})")
                
                # Get sample data
                cursor = conn.execute("SELECT * FROM videos LIMIT 1")
                sample = cursor.fetchone()
                if sample:
                    print(f"📝 Sample video data:")
                    for key in sample.keys():
                        value = sample[key]
                        if isinstance(value, str) and len(value) > 50:
                            value = value[:50] + "..."
                        print(f"   {key}: {value}")
            
            # Check subtitles table if exists
            if 'subtitles' in tables:
                cursor = conn.execute("SELECT COUNT(*) as count FROM subtitles")
                subtitle_count = cursor.fetchone()['count']
                print(f"📺 Subtitles: {subtitle_count} entries")
            
    except Exception as e:
        print(f"❌ Error checking {db_path}: {e}")

def main():
    downloads_dir = "yt2telegram/downloads"
    
    if not os.path.exists(downloads_dir):
        print(f"❌ Downloads directory not found: {downloads_dir}")
        return
    
    print(f"📁 Scanning directory: {downloads_dir}")
    
    db_files = [f for f in os.listdir(downloads_dir) if f.endswith('.db')]
    print(f"🗄️  Found {len(db_files)} database files: {db_files}")
    
    # Check first few databases
    for db_file in db_files[:3]:
        db_path = os.path.join(downloads_dir, db_file)
        check_database_schema(db_path)

if __name__ == "__main__":
    main()