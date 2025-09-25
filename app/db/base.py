
# app/db/base.py
from __future__ import annotations

import os
from datetime import datetime
from typing import AsyncIterator

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# --- Engine & Session (async) -------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./app.db")

engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=False, future=True)

SessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

async def get_async_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency to yield an AsyncSession with proper typing."""
    async with SessionLocal() as session:
        yield session

# --- Declarative Base ---------------------------------------------------------

class Base(DeclarativeBase):
    pass

# --- Baseline Tables (typed with Mapped[T]) ----------------------------------

class Audit(Base):
    __tablename__ = "audits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class ActionPlan(Base):
    __tablename__ = "action_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sender_email: Mapped[str] = mapped_column(String(320), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)  # keep|unsubscribe|delete
    reason: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class UndoWindow(Base):
    __tablename__ = "undo_windows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    decision_id: Mapped[int] = mapped_column(Integer, nullable=False)  # (FK can be added later)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
