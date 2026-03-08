"""
Project Colossal entry helper.

This file is optional. For the full app, run:
  - backend:   python -m uvicorn backend.main:app --reload
  - frontend:  streamlit run frontend/app.py

See README.md for details.
"""

from __future__ import annotations

import os


def main() -> None:
    print("Project Colossal")
    print("--------------")
    print(f"COLOSSAL_API_URL = {os.getenv('COLOSSAL_API_URL', 'http://127.0.0.1:8000')}")
    print("Backend:  python -m uvicorn backend.main:app --reload")
    print("Frontend: streamlit run frontend/app.py")


if __name__ == "__main__":
    main()

