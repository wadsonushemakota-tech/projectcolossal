# Project Colossal (Demo MVP)

Python-first web application for onboarding informal businesses, capturing digital transaction traces, generating creditworthiness profiles, minting usage tokens, and enabling micro-loan applications.

This repo contains:
- **FastAPI backend**: REST APIs, scoring, token logic, SQLite persistence
- **Streamlit frontend**: modern dashboard UX that consumes the backend APIs

## Quick start (Windows / PowerShell)

1) Create and activate a virtual environment

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2) Install dependencies

```bash
python -m pip install -r requirements.txt
```

3) Start the backend API (Terminal 1)

```bash
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

4) Start the frontend (Terminal 2)

```bash
streamlit run frontend/app.py
```

Open the UI at `http://localhost:8501`.

## What’s implemented

- Business onboarding (women-led and informal supported)
- Transaction ingestion (manual + CSV upload)
- Credit score + risk band (transparent feature breakdown)
- Token earning ledger based on transaction activity
- Loan application flow + eligibility estimate
- Admin-style analytics (basic KPIs + charts)

## Data model (local)

Uses SQLite at `./data/colossal.db` by default.
You can override with `.env` (copy from `.env.example`).

## Notes for real-world deployment

- Replace SQLite with Postgres (same SQLModel layer)
- Add real EcoCash / bank integrations behind `backend/routes/transactions.py`
- Add KYC/AML, fraud detection, and consent flows
- Add authentication (e.g., OAuth2/JWT) and role-based access

