from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from dotenv import load_dotenv
from sqlmodel import Session, SQLModel, create_engine


load_dotenv()


def _db_url() -> str:
    return os.getenv("COLOSSAL_DB_URL", "sqlite:///./data/colossal_v3.db")


engine = create_engine(
    _db_url(),
    echo=False,
    connect_args={"check_same_thread": False} if _db_url().startswith("sqlite") else {},
)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


@contextmanager
def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session

