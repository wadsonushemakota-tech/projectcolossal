from __future__ import annotations

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from backend.db import get_session
from backend.models import Training, TrainingEnrollment


router = APIRouter(prefix="/trainings", tags=["trainings"])


@router.post("", response_model=Training)
def create_training(training: Training) -> Training:
    with get_session() as session:
        session.add(training)
        session.commit()
        session.refresh(training)
        return training


@router.get("", response_model=List[Training])
def list_trainings() -> List[Training]:
    with get_session() as session:
        return list(session.exec(select(Training)))


@router.get("/{training_id}", response_model=Training)
def get_training(training_id: int) -> Training:
    with get_session() as session:
        t = session.get(Training, training_id)
        if not t:
            raise HTTPException(status_code=404, detail="Training not found")
        return t


@router.post("/{training_id}/enroll", response_model=TrainingEnrollment)
def enroll_in_training(training_id: int, business_id: int) -> TrainingEnrollment:
    with get_session() as session:
        t = session.get(Training, training_id)
        if not t:
            raise HTTPException(status_code=404, detail="Training not found")
        
        enrollment = TrainingEnrollment(
            business_id=business_id,
            training_id=training_id,
            enrolled_at=datetime.utcnow(),
            status="pending"
        )
        session.add(enrollment)
        session.commit()
        session.refresh(enrollment)
        return enrollment


@router.get("/enrollments/{business_id}", response_model=List[TrainingEnrollment])
def list_enrollments(business_id: int) -> List[TrainingEnrollment]:
    with get_session() as session:
        stmt = select(TrainingEnrollment).where(TrainingEnrollment.business_id == business_id)
        return list(session.exec(stmt))


@router.post("/enrollments/{enrollment_id}/progress")
def update_progress(
    enrollment_id: int, 
    progress: float, 
    status: Optional[str] = None,
    current_stage: Optional[int] = None
) -> TrainingEnrollment:
    with get_session() as session:
        e = session.get(TrainingEnrollment, enrollment_id)
        if not e:
            raise HTTPException(status_code=404, detail="Enrollment not found")
        e.progress = progress
        if status:
            e.status = status
        if current_stage is not None:
            e.current_stage = current_stage
        session.add(e)
        session.commit()
        session.refresh(e)
        return e
