from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlmodel import col, select

from backend.db import get_session
from backend.models import CreditProfile, TokenLedgerEntry, Transaction, TransactionBase, TransactionType
from backend.scoring import compute_credit_score, score_to_json
from backend.tokenomics import tokens_for_transaction


router = APIRouter(prefix="/businesses/{business_id}", tags=["transactions"])


class TransactionCreate(TransactionBase):
    ts: datetime = Field(default_factory=datetime.utcnow)


class BulkIngestResult(BaseModel):
    created: int
    skipped: int
    errors: List[str]


class WalletSummary(BaseModel):
    tokens_balance: int
    earned_total: int


class CreditProfileOut(BaseModel):
    business_id: int
    score: int
    risk_band: str
    confidence: float
    last_computed_at: datetime
    features: Dict[str, Any]


def _tokens_balance(session) -> int:
    rows = session.exec(select(TokenLedgerEntry.tokens_delta))
    return int(sum(rows))


@router.post("/transactions", response_model=Transaction)
def add_transaction(business_id: int, payload: TransactionCreate) -> Transaction:
    if payload.business_id != business_id:
        raise HTTPException(status_code=400, detail="business_id mismatch")

    with get_session() as session:
        tx = Transaction.model_validate(payload.model_dump())
        session.add(tx)
        session.commit()
        session.refresh(tx)

        token_res = tokens_for_transaction(tx)
        if token_res.tokens > 0:
            entry = TokenLedgerEntry(
                business_id=business_id,
                tokens_delta=token_res.tokens,
                reason=token_res.reason,
                tx_id=tx.id,
            )
            session.add(entry)
            session.commit()

        return tx


@router.get("/transactions", response_model=List[Transaction])
def list_transactions(
    business_id: int,
    type: Optional[TransactionType] = None,
    limit: int = 200,
    offset: int = 0,
) -> List[Transaction]:
    with get_session() as session:
        stmt = (
            select(Transaction)
            .where(Transaction.business_id == business_id)
            .order_by(col(Transaction.ts).desc())
            .offset(offset)
            .limit(limit)
        )
        if type:
            stmt = stmt.where(Transaction.type == type)
        return list(session.exec(stmt))


@router.post("/transactions/upload_csv", response_model=BulkIngestResult)
async def upload_transactions_csv(business_id: int, file: UploadFile = File(...)) -> BulkIngestResult:
    """
    CSV columns (header required):
      ts (ISO8601), type, amount, currency, channel, reference, counterparty
    """
    raw = await file.read()
    text = raw.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    created = 0
    skipped = 0
    errors: List[str] = []

    with get_session() as session:
        for i, row in enumerate(reader, start=2):  # 1 header
            try:
                ts = datetime.fromisoformat((row.get("ts") or "").replace("Z", "+00:00"))
                ttype = TransactionType((row.get("type") or "other").strip())
                amount = float(row.get("amount") or "0")
                currency = (row.get("currency") or "ZWL").strip() or "ZWL"
                channel = (row.get("channel") or "").strip() or None
                reference = (row.get("reference") or "").strip() or None
                counterparty = (row.get("counterparty") or "").strip() or None

                if amount == 0:
                    skipped += 1
                    continue

                tx = Transaction(
                    business_id=business_id,
                    ts=ts,
                    type=ttype,
                    amount=amount,
                    currency=currency,
                    channel=channel,
                    reference=reference,
                    counterparty=counterparty,
                )
                session.add(tx)
                session.commit()
                session.refresh(tx)
                created += 1

                token_res = tokens_for_transaction(tx)
                if token_res.tokens > 0:
                    session.add(
                        TokenLedgerEntry(
                            business_id=business_id,
                            tokens_delta=token_res.tokens,
                            reason=token_res.reason,
                            tx_id=tx.id,
                        )
                    )
                    session.commit()
            except Exception as e:
                errors.append(f"Line {i}: {e}")

    return BulkIngestResult(created=created, skipped=skipped, errors=errors)


@router.get("/wallet", response_model=WalletSummary)
def wallet(business_id: int) -> WalletSummary:
    with get_session() as session:
        stmt = select(TokenLedgerEntry).where(TokenLedgerEntry.business_id == business_id)
        entries = list(session.exec(stmt))
        earned_total = sum(e.tokens_delta for e in entries if e.tokens_delta > 0)
        return WalletSummary(tokens_balance=int(sum(e.tokens_delta for e in entries)), earned_total=int(earned_total))


@router.post("/credit-profile/compute", response_model=CreditProfileOut)
def compute_profile(business_id: int) -> CreditProfileOut:
    with get_session() as session:
        res = compute_credit_score(session=session, business_id=business_id)

        existing = session.get(CreditProfile, business_id)
        if existing:
            existing.score = int(res.score)
            existing.risk_band = res.risk_band
            existing.confidence = float(res.confidence)
            existing.last_computed_at = datetime.utcnow()
            existing.features_json = score_to_json(res.features)
            session.add(existing)
        else:
            session.add(
                CreditProfile(
                    business_id=business_id,
                    score=int(res.score),
                    risk_band=res.risk_band,
                    confidence=float(res.confidence),
                    last_computed_at=datetime.utcnow(),
                    features_json=score_to_json(res.features),
                )
            )
        session.commit()

        return CreditProfileOut(
            business_id=business_id,
            score=int(res.score),
            risk_band=res.risk_band,
            confidence=float(res.confidence),
            last_computed_at=datetime.utcnow(),
            features=res.features,
        )


@router.get("/credit-profile", response_model=CreditProfileOut)
def get_profile(business_id: int) -> CreditProfileOut:
    with get_session() as session:
        p = session.get(CreditProfile, business_id)
        if not p:
            raise HTTPException(status_code=404, detail="Credit profile not found. Compute it first.")
        features = {}
        try:
            import json

            features = json.loads(p.features_json or "{}")
        except Exception:
            features = {}
        return CreditProfileOut(
            business_id=business_id,
            score=int(p.score),
            risk_band=p.risk_band,
            confidence=float(p.confidence),
            last_computed_at=p.last_computed_at,
            features=features,
        )

