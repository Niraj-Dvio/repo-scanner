# PowerShell starter: activates .venv if present then runs uvicorn
if (Test-Path ".\.venv\Scripts\Activate.ps1") {
    . .\.venv\Scripts\Activate.ps1
}
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
