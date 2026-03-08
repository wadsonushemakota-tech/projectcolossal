
from __future__ import annotations

from typing import Any, Dict, List, Optional

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import col, select

from backend.db import get_session
from backend.models import CreditProfile, LoanApplication, LoanApplicationBase, LoanStatus, TokenLedgerEntry
from backend.scoring import compute_credit_score, loan_offer_from_score, score_to_json


router = APIRouter(prefix="/businesses/{business_id}", tags=["loans"])


class LoanOffer(BaseModel):
    max_amount: float
    recommended_term_months: int
    basis: Dict[str, Any]


class LoanApplicationOut(BaseModel):
    id: int
    business_id: int
    amount: float
    currency: str
    term_months: int
    purpose: str
    status: LoanStatus
    created_at: datetime
    decision_reason: Optional[str]


@router.get("/loan-offer", response_model=LoanOffer)
def loan_offer(business_id: int) -> LoanOffer:
    with get_session() as session:
        # tokens
        entries = list(
            session.exec(select(TokenLedgerEntry).where(TokenLedgerEntry.business_id == business_id))
        )
        tokens = int(sum(e.tokens_delta for e in entries))

        # profile (compute if missing)
        profile = session.get(CreditProfile, business_id)
        if not profile:
            res = compute_credit_score(session=session, business_id=business_id)
            profile = CreditProfile(
                business_id=business_id,
                score=int(res.score),
                risk_band=res.risk_band,
                confidence=float(res.confidence),
                last_computed_at=datetime.utcnow(),
                features_json=score_to_json(res.features),
            )
            session.add(profile)
            session.commit()
        max_amount, term = loan_offer_from_score(int(profile.score), tokens=tokens)
        return LoanOffer(
            max_amount=max_amount,
            recommended_term_months=term,
            basis={
                "score": int(profile.score),
                "risk_band": profile.risk_band,
                "confidence": float(profile.confidence),
                "tokens_balance": tokens,
            },
        )


@router.post("/loans", response_model=LoanApplicationOut)
def apply_for_loan(business_id: int, payload: LoanApplicationBase) -> LoanApplicationOut:
    if payload.business_id != business_id:
        raise HTTPException(status_code=400, detail="business_id mismatch")

    with get_session() as session:
        # gather eligibility signals
        entries = list(session.exec(select(TokenLedgerEntry).where(TokenLedgerEntry.business_id == business_id)))
        tokens = int(sum(e.tokens_delta for e in entries))

        profile = session.get(CreditProfile, business_id)
        if not profile:
            res = compute_credit_score(session=session, business_id=business_id)
            profile = CreditProfile(
                business_id=business_id,
                score=int(res.score),
                risk_band=res.risk_band,
                confidence=float(res.confidence),
                last_computed_at=datetime.utcnow(),
                features_json=score_to_json(res.features),
            )
            session.add(profile)
            session.commit()

        offer_max, _ = loan_offer_from_score(int(profile.score), tokens=tokens)

        # basic rules for demo (real system: underwriting + fraud + KYC + capital provider constraints)
        if payload.amount <= 0:
            raise HTTPException(status_code=400, detail="Invalid amount")
        if payload.amount > offer_max:
            status = LoanStatus.rejected
            reason = f"Requested amount exceeds eligible maximum ({offer_max})."
        elif int(profile.score) < 600:
            status = LoanStatus.rejected
            reason = "Credit score below minimum threshold."
        elif tokens < 100:
            status = LoanStatus.rejected
            reason = "Insufficient token history for underwriting."
        else:
            status = LoanStatus.submitted
            reason = "Submitted for review."

        app = LoanApplication(
            business_id=business_id,
            amount=float(payload.amount),
            currency=payload.currency,
            term_months=int(payload.term_months),
            purpose=payload.purpose,
            status=status,
            created_at=datetime.utcnow(),
            decision_reason=reason,
        )
        session.add(app)
        session.commit()
        session.refresh(app)

        return LoanApplicationOut(
            id=int(app.id),
            business_id=business_id,
            amount=float(app.amount),
            currency=app.currency,
            term_months=int(app.term_months),
            purpose=app.purpose,
            status=app.status,
            created_at=app.created_at,
            decision_reason=app.decision_reason,
        )


@router.get("/loans", response_model=List[LoanApplicationOut])
def list_loans(business_id: int, limit: int = 50, offset: int = 0) -> List[LoanApplicationOut]:
    with get_session() as session:
        apps = list(
            session.exec(
                select(LoanApplication)
                .where(LoanApplication.business_id == business_id)
                .order_by(col(LoanApplication.created_at).desc())
                .offset(offset)
                .limit(limit)
            )
        )
        return [
            LoanApplicationOut(
                id=int(a.id),
                business_id=a.business_id,
                amount=float(a.amount),
                currency=a.currency,
                term_months=int(a.term_months),
                purpose=a.purpose,
                status=a.status,
                created_at=a.created_at,
                decision_reason=a.decision_reason,
            )
            for a in apps
        ]

