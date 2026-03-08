from __future__ import annotations

from dataclasses import dataclass

from backend.models import Transaction, TransactionType


@dataclass(frozen=True)
class TokenResult:
    tokens: int
    reason: str


def tokens_for_transaction(tx: Transaction) -> TokenResult:
    """
    Simple, explainable token rule-set.

    - Encourages digital payments + consistent usage
    - Keeps reward bounded and auditable
    """
    amt = abs(float(tx.amount))

    # baseline: 1 token per 10 currency units, capped per-transaction
    baseline = min(250, int(amt // 10))

    # multipliers by transaction type (incentives)
    multiplier = 1.0
    if tx.type in {TransactionType.merchant_payment}:
        multiplier = 1.25
    elif tx.type in {TransactionType.p2p_in, TransactionType.p2p_out}:
        multiplier = 1.10
    elif tx.type in {TransactionType.airtime, TransactionType.data}:
        multiplier = 1.05
    elif tx.type in {TransactionType.cash_in, TransactionType.cash_out}:
        multiplier = 0.90

    earned = int(round(baseline * multiplier))
    earned = max(0, min(earned, 300))

    reason = f"Earned from {tx.type.value} (amount={amt:.2f})"
    return TokenResult(tokens=earned, reason=reason)

