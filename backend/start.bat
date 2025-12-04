@echo off
REM Activate virtualenv if present, then run uvicorn
if exist ".venv\Scripts\activate.bat" (
  call .venv\Scripts\activate.bat
)
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
pause
