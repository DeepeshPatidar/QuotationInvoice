# Quotation Manager - Build Script for PowerShell
# Run: .\build.ps1

Write-Host ""
Write-Host "==============================================="
Write-Host " Apex Quotation Manager - EXE Build Script"
Write-Host "==============================================="
Write-Host ""

# Check Python
Write-Host "Checking Python installation..."
$pythonCheck = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python not found. Please install Python 3.8+"
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "✓ Python found: $pythonCheck"
Write-Host ""

# Install PyInstaller
Write-Host "Ensuring PyInstaller is installed..."
$pipCheck = pip show pyinstaller 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing PyInstaller (first time only)..."
    pip install pyinstaller --quiet
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to install PyInstaller"
        Read-Host "Press Enter to exit"
        exit 1
    }
}
Write-Host "✓ PyInstaller ready"
Write-Host ""

# Build
Write-Host "Building QuotationManager.exe..."
Write-Host "This may take 2-5 minutes, please wait..."
Write-Host ""

python build_exe.py

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Build failed"
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "==============================================="
Write-Host " ✓ BUILD SUCCESSFUL!"
Write-Host "==============================================="
Write-Host ""
Write-Host "✓ Created: dist/QuotationManager.exe"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Test: .\dist\QuotationManager.exe"
Write-Host "  2. Share with users or create installer"
Write-Host ""
Write-Host "To create a professional installer:"
Write-Host "  - Install NSIS: https://nsis.sourceforge.io/"
Write-Host "  - Run: & 'C:\Program Files (x86)\NSIS\makensis.exe' installer.nsi"
Write-Host ""

Read-Host "Press Enter to exit"
