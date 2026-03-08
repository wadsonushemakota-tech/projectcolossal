from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from sqlmodel import col, select

from backend.db import get_session
from backend.models import Business, BusinessBase


router = APIRouter(prefix="/businesses", tags=["businesses"])


@router.post("", response_model=Business)
def create_business(payload: BusinessBase) -> Business:
    with get_session() as session:
        b = Business.model_validate(payload.model_dump())
        session.add(b)
        session.commit()
        session.refresh(b)
        return b


@router.get("", response_model=List[Business])
def list_businesses(q: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[Business]:
    with get_session() as session:
        stmt = select(Business).order_by(col(Business.created_at).desc()).offset(offset).limit(limit)
        if q:
            like = f"%{q.strip()}%"
            stmt = stmt.where(
                col(Business.name).ilike(like)
                | col(Business.owner_name).ilike(like)
                | col(Business.phone).ilike(like)
            )
        return list(session.exec(stmt))


@router.get("/{business_id}", response_model=Business)
def get_business(business_id: int) -> Business:
    with get_session() as session:
        b = session.get(Business, business_id)
        if not b:
            raise HTTPException(status_code=404, detail="Business not found")
        return b

