#!/usr/bin/env bash
# One-click launcher: creates a venv on first run, installs deps, starts the app.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
    echo "First run: creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -e ".[dev]"
else
    source .venv/bin/activate
fi

if [ ! -f .env ]; then
    echo "WARNING: no .env file found. Copy .env.example to .env and add your ANTHROPIC_API_KEY."
fi

python -m receipt_expense.app
