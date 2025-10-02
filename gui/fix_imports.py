#!/usr/bin/env python3
"""Script to fix relative imports in the GUI package."""

import os
import re

def fix_imports_in_file(filepath):
    """Fix relative imports in a single file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix relative imports
    content = re.sub(r'from \.\.\.utils\.', 'from utils.', content)
    content = re.sub(r'from \.\.\.core\.', 'from core.', content)
    content = re.sub(r'from \.\.\.services\.', 'from services.', content)
    content = re.sub(r'from \.\.\.main import', 'from main import', content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Fixed imports in {filepath}")

def main():
    """Fix imports in all router files."""
    router_dir = "api/routers"
    
    for filename in os.listdir(router_dir):
        if filename.endswith('.py'):
            filepath = os.path.join(router_dir, filename)
            fix_imports_in_file(filepath)
    
    print("All imports fixed!")

if __name__ == "__main__":
    main()