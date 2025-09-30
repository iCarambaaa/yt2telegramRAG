import sys
sys.path.insert(0, 'gui')

print("Reading file...")
with open('gui/core/database_manager.py', 'r') as f:
    content = f.read()

print(f"File length: {len(content)} characters")
print("First 200 characters:")
print(content[:200])
print("\nLast 200 characters:")
print(content[-200:])

print("\nChecking for class definition...")
if 'class DatabaseManager:' in content:
    print("✓ DatabaseManager class found in file")
else:
    print("❌ DatabaseManager class NOT found in file")

print("\nTrying to execute...")
try:
    exec(content)
    print("✓ File executed successfully")
    if 'DatabaseManager' in locals():
        print("✓ DatabaseManager is in locals")
        db = DatabaseManager()
        print("✓ DatabaseManager instance created")
    else:
        print("❌ DatabaseManager not in locals")
        print("Available names:", [name for name in locals().keys() if not name.startswith('_')])
except Exception as e:
    print(f"❌ Execution failed: {e}")
    import traceback
    traceback.print_exc()