@echo off
echo ============================================
echo   Quotation App - Environment Setup
echo ============================================

REM Step 1: Create virtual environment if not exists
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

REM Step 2: Activate virtual environment
call venv\Scripts\activate

REM Step 3: Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Step 4: Install requirements
echo Installing dependencies...
pip install -r requirements.txt

echo --------------------------------------------
echo Setup complete!
echo To run the app:
echo   call venv\Scripts\activate
echo   python Quote.py
echo --------------------------------------------
pause
