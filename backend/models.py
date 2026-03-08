from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import EmailStr
from sqlmodel import Field, SQLModel


class TransactionType(str, Enum):
    airtime = "airtime"
    data = "data"
    merchant_payment = "merchant_payment"
    p2p_in = "p2p_in"
    p2p_out = "p2p_out"
    cash_in = "cash_in"
    cash_out = "cash_out"
    purchase_supply = "purchase_supply"
    tax_payment = "tax_payment"
    other = "other"


class LoanStatus(str, Enum):
    draft = "draft"
    submitted = "submitted"
    approved = "approved"
    rejected = "rejected"
    disbursed = "disbursed"
    closed = "closed"


class BusinessBase(SQLModel):
    name: str
    owner_name: str
    phone: str
    gender: Optional[str] = None
    email: Optional[EmailStr] = None
    location: Optional[str] = None
    category: Optional[str] = None
    is_registered: bool = False
    zimra_tin: Optional[str] = None
    zimra_tax_number: Optional[str] = None


class Business(BusinessBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class Training(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: str
    requirements: str = "" # Prerequisites or tools needed
    content: str = "" # Overall course introduction
    stages_json: str = "[]" # JSON list of {title, video_url, content}
    cost: float
    currency: str = "USD"
    module_outline: str  # Markdown or newline-separated text


class TrainingEnrollment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    business_id: int = Field(index=True, foreign_key="business.id")
    training_id: int = Field(index=True, foreign_key="training.id")
    enrolled_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    status: str = "pending"  # pending, in_progress, completed
    progress: float = 0.0 # 0 to 100
    current_stage: int = 0 # Index of the current stage


class TransactionBase(SQLModel):
    business_id: int = Field(index=True, foreign_key="business.id")
    ts: datetime = Field(default_factory=datetime.utcnow, index=True)
    type: TransactionType = Field(default=TransactionType.other, index=True)
    amount: float
    currency: str = "ZWL"
    channel: Optional[str] = None  # e.g. EcoCash, Steward, POS
    reference: Optional[str] = None
    counterparty: Optional[str] = None

    
class Transaction(TransactionBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)


class TokenLedgerEntry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    business_id: int = Field(index=True, foreign_key="business.id")
    ts: datetime = Field(default_factory=datetime.utcnow, index=True)
    tokens_delta: int
    reason: str
    tx_id: Optional[int] = Field(default=None, foreign_key="transaction.id")


class CreditProfile(SQLModel, table=True):
    business_id: int = Field(primary_key=True, foreign_key="business.id")
    score: int = Field(index=True)  # 300..850
    risk_band: str = Field(index=True)  # low/medium/high
    confidence: float = Field(ge=0, le=1)
    last_computed_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    features_json: str = "{}"


class LoanApplicationBase(SQLModel):
    business_id: int = Field(index=True, foreign_key="business.id")
    amount: float
    currency: str = "ZWL"
    term_months: int = 3
    purpose: str


class LoanApplication(LoanApplicationBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    status: LoanStatus = Field(default=LoanStatus.submitted, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    decision_reason: Optional[str] = None

