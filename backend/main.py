from __future__ import annotations 

from fastapi import FastAPI

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db import init_db
from backend.routes.businesses import router as businesses_router
from backend.routes.health import router as health_router
from backend.routes.loans import router as loans_router
from backend.routes.transactions import router as transactions_router
from backend.routes.trainings import router as trainings_router


load_dotenv()

app = FastAPI(
    title="Project Colossal API",
    version="0.1.0",
    description="APIs for onboarding informal businesses, transaction trace capture, credit scoring, tokenomics, and micro-loans.",
)

origins = [
    os.getenv("COLOSSAL_FRONTEND_ORIGIN", "http://localhost:8501"),
    "http://127.0.0.1:8501",
    "http://localhost:8501",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/")
def root() -> dict:
    return {"name": "Project Colossal API", "docs": "/docs", "health": "/health"}


app.include_router(health_router)
app.include_router(businesses_router)
app.include_router(transactions_router)
app.include_router(loans_router)
app.include_router(trainings_router)



# # 2) Run backend on the port the frontend expects (8001)
# python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001 --reload

# # 3) In another terminal, run the frontend
# python -m streamlit run frontend/app.py --server.port 8501