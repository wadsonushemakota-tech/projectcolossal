$ErrorActionPreference = "Stop"

Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)

python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000

