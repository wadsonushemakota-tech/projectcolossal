
import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

from sqlmodel import Session, select

from backend.models import Transaction, TransactionType


@dataclass
class ScoreResult:
    score: int
    risk_band: str
    confidence: float
    features: Dict[str, Any]


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _risk_band(score: int) -> str:
    if score >= 720:
        return "low"
    if score >= 600:
        return "medium"
    return "high"


def _days_covered(txs: List[Transaction]) -> int:
    if not txs:
        return 0
    lo = min(t.ts for t in txs)
    hi = max(t.ts for t in txs)
    return max(1, (hi - lo).days + 1)


def _monthlyized_volume(txs: List[Transaction]) -> float:
    if not txs:
        return 0.0
    days = _days_covered(txs)
    total = sum(abs(t.amount) for t in txs)
    return total * (30.0 / float(days))


def _consistency(txs: List[Transaction]) -> float:
    """
    Consistency proxy: fraction of active weeks in lookback window.
    """
    if not txs:
        return 0.0
    lo = min(t.ts for t in txs)
    hi = max(t.ts for t in txs)
    weeks = max(1, math.ceil((hi - lo).days / 7))
    active = set((t.ts.isocalendar().year, t.ts.isocalendar().week) for t in txs)
    return _clamp(len(active) / float(weeks), 0.0, 1.0)


def _diversity(txs: List[Transaction]) -> float:
    if not txs:
        return 0.0
    types = set(t.type for t in txs)
    # cap at 6 types for saturation
    return _clamp(len(types) / 6.0, 0.0, 1.0)


def _inflow_outflow_balance(txs: List[Transaction]) -> float:
    """
    Approximate by treating certain types as inflow/outflow when explicit sign isn't used.
    """
    if not txs:
        return 0.0
    inflow_types = {TransactionType.p2p_in, TransactionType.cash_in}
    outflow_types = {
        TransactionType.p2p_out,
        TransactionType.cash_out,
        TransactionType.airtime,
        TransactionType.data,
        TransactionType.merchant_payment,
        TransactionType.purchase_supply,
        TransactionType.tax_payment,
    }
    inflow = 0.0
    outflow = 0.0
    for t in txs:
        if t.amount < 0:
            outflow += abs(t.amount)
            continue
        if t.type in inflow_types:
            inflow += t.amount
        elif t.type in outflow_types:
            outflow += t.amount
        else:
            # unknown: count as neutral volume
            inflow += 0.5 * t.amount
            outflow += 0.5 * t.amount
    denom = inflow + outflow
    if denom <= 0:
        return 0.0
    # best around mild surplus inflow; penalize extreme imbalance
    ratio = inflow / denom  # 0..1
    return 1.0 - (abs(ratio - 0.55) / 0.55)  # peak at 0.55


def compute_credit_score(session: Session, business_id: int, lookback_days: int = 180) -> ScoreResult:
    since = datetime.utcnow() - timedelta(days=lookback_days)
    txs = list(
        session.exec(
            select(Transaction)
            .where(Transaction.business_id == business_id)
            .where(Transaction.ts >= since)
            .order_by(Transaction.ts.asc())
        )
    )

    days = _days_covered(txs)
    tx_count = len(txs)
    vol_m = _monthlyized_volume(txs)
    consistency = _consistency(txs)
    diversity = _diversity(txs)
    balance = _clamp(_inflow_outflow_balance(txs), 0.0, 1.0)

    # Simple, explainable model (placeholder for ML / bureau-grade scoring).
    # Produce 300..850.
    vol_score = _clamp(math.log1p(vol_m) / math.log(1 + 50000), 0.0, 1.0)
    activity_score = _clamp(tx_count / 250.0, 0.0, 1.0)
    tenure_score = _clamp(days / 180.0, 0.0, 1.0)

    blended = (
        0.30 * vol_score
        + 0.20 * activity_score
        + 0.20 * consistency
        + 0.15 * diversity
        + 0.10 * balance
        + 0.05 * tenure_score
    )
    score = int(round(300 + 550 * blended))

    # Confidence increases with data quantity and coverage.
    confidence = _clamp(0.15 + 0.45 * tenure_score + 0.40 * activity_score, 0.0, 1.0)

    features: Dict[str, Any] = {
        "lookback_days": lookback_days,
        "tx_count": tx_count,
        "days_covered": days,
        "monthlyized_volume": round(vol_m, 2),
        "consistency": round(consistency, 3),
        "diversity": round(diversity, 3),
        "inflow_outflow_balance": round(balance, 3),
        "subscores": {
            "volume": round(vol_score, 3),
            "activity": round(activity_score, 3),
            "tenure": round(tenure_score, 3),
        },
    }

    score = int(max(300, min(850, score)))
    return ScoreResult(
        score=score,
        risk_band=_risk_band(score),
        confidence=float(confidence),
        features=features,
    )


def score_to_json(features: Dict[str, Any]) -> str:
    return json.dumps(features, ensure_ascii=False, separators=(",", ":"))


def loan_offer_from_score(score: int, tokens: int) -> Tuple[float, int]:
    """
    Conservative eligibility estimate.
    Returns (max_amount, term_months).
    """
    # base from score
    if score >= 740:
        base = 2500.0
        term = 9
    elif score >= 680:
        base = 1500.0
        term = 6
    elif score >= 600:
        base = 800.0
        term = 4
    else:
        base = 200.0
        term = 3

    # tokens act as a usage/collateral proxy
    boost = min(1.5, 1.0 + (tokens / 5000.0))
    return round(base * boost, 2), term

