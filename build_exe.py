"""
Build script to convert Quote.py into a standalone executable using PyInstaller
Run this script to generate the .exe file

Usage:
    python build_exe.py              # Build with default settings
    python build_exe.py --onedir     # Build as directory instead of single file
"""
import subprocess
import sys
import os
import shutil
import platform

def check_os():
    """Ensure we're on Windows"""
    if platform.system() != "Windows":
        print("ERROR: This build script only works on Windows")
        print("Current OS:", platform.system())
        sys.exit(1)

def install_pyinstaller():
    """Install PyInstaller if not present"""
    try:
        import PyInstaller
        print("✓ PyInstaller already installed")
        return True
    except ImportError:
        print("Installing PyInstaller...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("✓ PyInstaller installed successfully")
            return True
        except Exception as e:
            print(f"✗ Failed to install PyInstaller: {e}")
            return False

def clean_build_dirs():
    """Clean up old build artifacts"""
    dirs_to_clean = ["build", "dist", "QuotationManager.spec"]
    for item in dirs_to_clean:
        if os.path.exists(item):
            if os.path.isdir(item):
                print(f"  Removing old {item}/ directory...")
                shutil.rmtree(item)
            else:
                print(f"  Removing old {item}...")
                os.remove(item)

def build_executable():
    """Build the standalone executable using PyInstaller"""
    
    print("\n" + "="*60)
    print(" Apex Quotation Manager - EXE Build")
    print("="*60 + "\n")
    
    # Check OS
    print("Checking system...")
    check_os()
    print("✓ Windows detected\n")
    
    # Install PyInstaller
    print("Checking PyInstaller...")
    if not install_pyinstaller():
        sys.exit(1)
    print()
    
    # Clean old builds
    print("Cleaning old build artifacts...")
    clean_build_dirs()
    print()
    
    # Prepare build command with platform-specific path separator
    sep = ";" if platform.system() == "Windows" else ":"
    
    build_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",                          # Create single executable
        "--windowed",                         # No console window
        "--name=QuotationManager",            # Executable name
        "--distpath=./dist",                  # Output directory
        "--workpath=./build",                 # Build directory for current PyInstaller
        "--specpath=./",                      # Spec file location
        f"--add-data=quotation.db{sep}.",     # Include database
        f"--add-data=DSUB9PIN.png{sep}.",     # Include logo
        f"--add-data=templates{sep}templates",  # Include LaTeX templates
        "--hidden-import=PyQt6",              # Hidden imports
        "--hidden-import=jinja2",
        "--hidden-import=python_dateutil",
        "--hidden-import=PIL",
        "--hidden-import=charset_normalizer",
        "--hidden-import=dateutil",
        "Quote.py"
    ]
    
    print("Building executable...")
    print("This may take 2-5 minutes on first run...")
    print()
    
    try:
        result = subprocess.run(build_cmd, check=False)
        print()
        
        if result.returncode == 0:
            exe_path = os.path.join("dist", "QuotationManager.exe")
            if os.path.exists(exe_path):
                file_size_mb = os.path.getsize(exe_path) / (1024 * 1024)
                print("="*60)
                print(" ✓ BUILD SUCCESSFUL!")
                print("="*60)
                print(f"\nExecutable: {exe_path}")
                print(f"Size: {file_size_mb:.1f} MB")
                print("\nYou can now:")
                print(f"  1. Run directly: .\\dist\\QuotationManager.exe")
                print(f"  2. Test it thoroughly")
                print(f"  3. Share with users or create installer")
                print()
            else:
                print("✗ Build completed but executable not found")
                sys.exit(1)
        else:
            print("="*60)
            print(" ✗ BUILD FAILED")
            print("="*60)
            print("\nPossible solutions:")
            print("  1. Ensure all dependencies are installed: pip install -r requirements.txt")
            print("  2. Check that Quote.py can run normally: python Quote.py")
            print("  3. Try: pip install --upgrade pyinstaller")
            sys.exit(1)
            
    except Exception as e:
        print(f"✗ Error during build: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        build_executable()
    except KeyboardInterrupt:
        print("\n\nBuild cancelled by user")
        sys.exit(1)
