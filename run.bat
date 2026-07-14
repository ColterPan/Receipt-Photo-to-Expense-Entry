@echo off
rem One-click launcher: creates a venv on first run, installs deps, starts the app.
cd /d "%~dp0"

if not exist .venv (
    echo First run: creating virtual environment...
    py -3 -m venv .venv || python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -e ".[dev]"
) else (
    call .venv\Scripts\activate.bat
)

if not exist .env (
    echo.
    echo WARNING: no .env file found. Copy .env.example to .env and add your ANTHROPIC_API_KEY.
    echo.
)

python -m receipt_expense.app
pause
