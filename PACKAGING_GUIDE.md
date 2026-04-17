# How to Package Quotation Manager as .EXE Installer

This guide explains how to convert the Python application into professional .EXE files that can be installed on any Windows computer.

## Overview

There are two ways to distribute your application:

1. **Simple Method**: Create a standalone .EXE file (quick, self-contained)
2. **Professional Method**: Create a professional installer with Start Menu shortcuts, uninstall option, etc.

---

## Method 1: Simple Standalone .EXE (Recommended for Testing)

### Step 1: Install PyInstaller
Open PowerShell in the application directory and run:

```powershell
pip install pyinstaller
```

### Step 2: Build the Executable
Run the build script:

```powershell
python build_exe.py
```

This will create:
- `dist/QuotationManager.exe` - Your standalone executable

### Result
- Single .EXE file (~200-300 MB)
- Can be run directly on any Windows computer
- No installation needed
- Database files will be stored in: `%APPDATA%\ApexAutomobile\QuotationManager\`

### To Distribute
Simply send the `QuotationManager.exe` file to users. They can run it immediately.

---

## Method 2: Professional Installer (Recommended for Production)

This creates a proper Windows installer with:
- Installation wizard
- Start Menu shortcuts
- Desktop shortcut
- Uninstall option
- Professional branding

### Prerequisites
1. **PyInstaller** (see Step 1 above)
2. **NSIS** (Nullsoft Scriptable Install System)
   - Download from: https://nsis.sourceforge.io/
   - Run the installer and complete installation

### Step 1: Build the Executable
```powershell
python build_exe.py
```

### Step 2: Build the Installer
After PyInstaller completes:

**If NSIS is installed:**
```powershell
# On Windows
"C:\Program Files (x86)\NSIS\makensis.exe" installer.nsi
```

**Or from the NSIS GUI:**
1. Open NSIS menu from Start
2. Click "Makensis"
3. Select `installer.nsi` from this folder
4. Click "Compile NSI files"

### Result
- `ApexQuotationManager-Installer.exe` - Professional installer
- Users can install using the standard Windows installer wizard
- Application goes to: `C:\Program Files\ApexAutomobile\QuotationManager\`
- Start Menu shortcut automatically created
- Uninstall option available in Control Panel

---

## Complete Build Instructions for Distribution

### Quick Build (One Command)
```powershell
# 1. Install PyInstaller
pip install pyinstaller

# 2. Build executable
python build_exe.py

# 3. Created files will be in ./dist/ folder
```

### Result Files

After building, you'll have:

```
dist/
├── QuotationManager.exe          ← Direct executable (Method 1)
└── [other supporting files]

ApexQuotationManager-Installer.exe  ← Professional installer (Method 2)
```

---

## Testing the Built Application

### Test Standalone EXE
```powershell
.\dist\QuotationManager.exe
```

### Test Installer
```powershell
.\ApexQuotationManager-Installer.exe
```

The installer will:
1. Ask where to install
2. Create Start Menu shortcuts
3. Save database in AppData folder
4. Allow uninstallation from Control Panel > Programs

---

## Data & Database Files Location

When users run the installed application:

**Standalone .EXE uses:**
- Database: `%APPDATA%\ApexAutomobile\QuotationManager\quotation.db`
- Quotations: `%APPDATA%\ApexAutomobile\QuotationManager\quotations\`
- Proforma: `%APPDATA%\ApexAutomobile\QuotationManager\Proform\`
- Tax Invoices: `%APPDATA%\ApexAutomobile\QuotationManager\TaxInvoice\`

**With Installer:**
- Same locations in AppData
- Executable in: `C:\Program Files\ApexAutomobile\QuotationManager\`

---

## File Size Expectations

- **Standalone .EXE**: 200-300 MB
- **Installer .EXE**: Similar size (contains the same executable)
- **Installed Size**: 250-350 MB total

---

## Troubleshooting

### "PyInstaller not found"
```powershell
pip install pyinstaller
```

### "NSIS not found"
1. Download NSIS: https://nsis.sourceforge.io/
2. Install it
3. NSIS will be available at: `C:\Program Files (x86)\NSIS\`

### Antivirus Warnings
- PyInstaller-generated .EXEs sometimes trigger false antivirus warnings
- This is normal and harmless
- Users with antivirus software should scan the downloaded file first

### Database File Not Found
- The application automatically creates the database in AppData
- First run may take a few seconds for initialization

---

## Customization Options

### Change Application Name
Edit `build_exe.py`:
```python
"--name=MyCustomName",  # Change this
```

### Add Custom Icon
1. Create a 256x256 .ICO file
2. Edit `build_exe.py` to add:
```python
"--icon=path/to/icon.ico",
```

### Change Installer Name
Edit `installer.nsi`:
```nsi
OutFile "MyInstallerName.exe"
```

---

## Distribution Checklist

- [ ] Run `python build_exe.py` successfully
- [ ] Test `dist/QuotationManager.exe` on your computer
- [ ] Test data saving/loading
- [ ] Test PDF generation
- [ ] Create installer with NSIS (optional)
- [ ] Test installer on clean Windows computer (if possible)
- [ ] Distribute `QuotationManager.exe` or `ApexQuotationManager-Installer.exe`

---

## Questions?

Common scenarios:

**Q: Do users need Python installed?**
A: No. The .EXE includes everything needed.

**Q: Can someone edit the source code?**
A: No. The .EXE is compiled and protected like any other Windows program.

**Q: Will it work on Windows 7/8/10/11?**
A: Yes, .EXEs work on any modern Windows system.

**Q: How to update the application?**
A: Rebuild the .EXE whenever code changes and redistribute it.

---

## Next Steps

1. Run: `python build_exe.py`
2. Check `dist/QuotationManager.exe` was created
3. Test it by running the .EXE
4. (Optional) Create professional installer using NSIS
5. Share the .EXE or installer with users
