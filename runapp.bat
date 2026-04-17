@echo off
echo ============================================
echo   Starting Quotation App
echo ============================================

REM Check if venv exists
if not exist venv (
    echo Virtual environment not found!
    echo Please run setup.bat first.
    pause
    exit /b
)

REM Activate virtual environment
call venv\Scripts\activate

REM Run the app
python Quote.py

REM Deactivate venv after closing app
deactivate

echo --------------------------------------------
echo Application closed.
pause
