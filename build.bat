@echo off
REM Build Quotation Manager as Standalone EXE
REM Run this file to create the executable

echo.
echo ========================================
echo  Apex Quotation Manager - Build Script
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/
    pause
    exit /b 1
)

echo ✓ Python found
echo.

REM Install PyInstaller if not present
echo Checking PyInstaller...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo ERROR: Failed to install PyInstaller
        pause
        exit /b 1
    )
)

echo ✓ PyInstaller ready
echo.

REM Build the executable
echo Building QuotationManager.exe...
echo This may take 2-5 minutes...
echo.

python build_exe.py

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo  ✓ BUILD SUCCESSFUL!
echo ========================================
echo.
echo Files created in: dist\
echo.
echo QuotationManager.exe is ready to use!
echo You can:
echo   1. Run it directly: dist\QuotationManager.exe
echo   2. Share it with anyone to install
echo   3. Create an installer using installer.nsi
echo.
pause
