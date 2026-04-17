; NSIS Installer Script for Quotation Manager
; This creates a professional installer for the application
; Download NSIS from: https://nsis.sourceforge.io/

!include "MUI2.nsh"
!include "x64.nsh"

; Basic Settings
Name "Apex Automobile Quotation Manager"
OutFile "ApexQuotationManager-Installer.exe"
InstallDir "$PROGRAMFILES\ApexAutomobile\QuotationManager"
InstallDirRegKey HKCU "Software\ApexAutomobile\QuotationManager" "InstallPath"

; Variables
Var StartMenuFolder

; UI Settings
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_STARTMENU Application $StartMenuFolder
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

; Version info
VIProductVersion "1.0.0.0"
VIAddVersionKey /LANG=${LANG_ENGLISH} "ProductName" "Apex Automobile Quotation Manager"
VIAddVersionKey /LANG=${LANG_ENGLISH} "CompanyName" "Apex Automobile Testing"
VIAddVersionKey /LANG=${LANG_ENGLISH} "FileDescription" "Professional Quotation and Invoice Management System"
VIAddVersionKey /LANG=${LANG_ENGLISH} "FileVersion" "1.0.0"

; Installation Section
Section "Install"
    SetOutPath "$INSTDIR"
    
    ; Copy main executable
    File "dist\QuotationManager.exe"
    
    ; Create directories for data files
    CreateDirectory "$APPDATA\ApexAutomobile\QuotationManager\quotations"
    CreateDirectory "$APPDATA\ApexAutomobile\QuotationManager\Proform"
    CreateDirectory "$APPDATA\ApexAutomobile\QuotationManager\TaxInvoice"
    
    ; Store installation path
    WriteRegStr HKCU "Software\ApexAutomobile\QuotationManager" "InstallPath" "$INSTDIR"
    
    ; Create Start Menu shortcuts
    !insertmacro MUI_STARTMENU_WRITE_BEGIN Application
        CreateDirectory "$SMPROGRAMS\$StartMenuFolder"
        CreateShortcut "$SMPROGRAMS\$StartMenuFolder\Quotation Manager.lnk" "$INSTDIR\QuotationManager.exe"
        CreateShortcut "$SMPROGRAMS\$StartMenuFolder\Uninstall.lnk" "$INSTDIR\uninstall.exe"
    !insertmacro MUI_STARTMENU_WRITE_END
    
    ; Create Desktop shortcut
    CreateShortcut "$DESKTOP\Quotation Manager.lnk" "$INSTDIR\QuotationManager.exe"
    
    ; Create uninstaller
    WriteUninstaller "$INSTDIR\uninstall.exe"
    
    ; Write uninstall registry keys
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\ApexQuotationManager" "DisplayName" "Apex Automobile Quotation Manager"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\ApexQuotationManager" "UninstallString" "$INSTDIR\uninstall.exe"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\ApexQuotationManager" "InstallLocation" "$INSTDIR"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\ApexQuotationManager" "DisplayVersion" "1.0.0"
    
SectionEnd

; Uninstall Section
Section "Uninstall"
    Delete "$INSTDIR\QuotationManager.exe"
    Delete "$INSTDIR\uninstall.exe"
    RMDir "$INSTDIR"
    
    ; Remove shortcuts
    !insertmacro MUI_STARTMENU_GETFOLDER Application $StartMenuFolder
    Delete "$SMPROGRAMS\$StartMenuFolder\Quotation Manager.lnk"
    Delete "$SMPROGRAMS\$StartMenuFolder\Uninstall.lnk"
    RMDir "$SMPROGRAMS\$StartMenuFolder"
    
    Delete "$DESKTOP\Quotation Manager.lnk"
    
    ; Remove registry keys
    DeleteRegKey HKCU "Software\ApexAutomobile\QuotationManager"
    DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\ApexQuotationManager"
    
SectionEnd
