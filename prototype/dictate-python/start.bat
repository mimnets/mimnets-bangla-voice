@echo off
cd /d "%~dp0"
echo Checking libraries...
python -m pip install -q -r requirements.txt
echo Starting Bangla Dictate...
python app.py
pause
