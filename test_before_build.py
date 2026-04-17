#!/usr/bin/env python3
"""
Simple test to verify the App can run before building
Run this to ensure there are no syntax errors before packaging
"""

import sys
import subprocess

def test_app():
    print("\nTesting Quote.py for syntax and import errors...")
    print("-" * 60)
    
    # Test 1: Syntax check
    print("\n1. Checking Python syntax...")
    result = subprocess.run([sys.executable, "-m", "py_compile", "Quote.py"], 
                          capture_output=True, text=True)
    if result.returncode == 0:
        print("   ✓ Syntax OK")
    else:
        print("   ✗ Syntax error found:")
        print(result.stderr)
        return False
    
    # Test 2: Import check
    print("\n2. Checking imports...")
    test_code = """
try:
    from Quote import QuotationsTab, CustomersTab, ItemsTab, InvoicesTab, ProformaInvoicesTab
    from quotation_tool import Database, QuotePDF, ProformaPDF
    print("   ✓ All imports successful")
except ImportError as e:
    print(f"   ✗ Import error: {e}")
    exit(1)
"""
    result = subprocess.run([sys.executable, "-c", test_code],
                          capture_output=True, text=True, cwd=".")
    if result.returncode == 0:
        print(result.stdout.strip())
    else:
        print("   ✗ Import failed:")
        print(result.stderr)
        return False
    
    # Test 3: Database check
    print("\n3. Checking database...")
    test_code = """
try:
    from quotation_tool import Database
    db = Database()
    print(f"   ✓ Database initialized")
except Exception as e:
    print(f"   ✗ Database error: {e}")
    exit(1)
"""
    result = subprocess.run([sys.executable, "-c", test_code],
                          capture_output=True, text=True, cwd=".")
    if result.returncode == 0:
        print(result.stdout.strip())
    else:
        print("   ✗ Database check failed:")
        print(result.stderr)
        return False
    
    return True

if __name__ == "__main__":
    print("\n" + "="*60)
    print(" APEX QUOTATION MANAGER - PRE-BUILD TEST")
    print("="*60)
    
    if test_app():
        print("\n" + "="*60)
        print(" ✓ ALL TESTS PASSED - Ready to build!")
        print("="*60)
        print("\nYou can now run: python build_exe.py")
        print("Or: .\\build.bat")
        sys.exit(0)
    else:
        print("\n" + "="*60)
        print(" ✗ TESTS FAILED - Fix errors before building")
        print("="*60)
        sys.exit(1)
