from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Float, Integer, String, func, select
from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from bot_config import get_settings


settings = get_settings()


class Base(AsyncAttrs, DeclarativeBase):
    pass


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    amount: Mapped[float] = mapped_column(Float)
    category: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class Subscription(Base):
    __tablename__ = "subscriptions"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    expires_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


engine = create_async_engine(settings.db_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def add_expense(user_id: int, amount: float, category: str) -> Expense:
    async with AsyncSessionLocal() as session:
        exp = Expense(user_id=user_id, amount=amount, category=category)
        session.add(exp)
        await session.commit()
        await session.refresh(exp)
        return exp


async def list_expenses(user_id: int, limit: int = 10) -> list[Expense]:
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(Expense)
            .where(Expense.user_id == user_id)
            .order_by(Expense.created_at.desc())
            .limit(limit)
        )
        return list(res.scalars().all())


async def stats_by_period(user_id: int, days: int = 7) -> dict[str, float]:
    since = dt.datetime.utcnow() - dt.timedelta(days=days)
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(
                Expense.category,
                func.sum(Expense.amount).label("total"),
            )
            .where(Expense.user_id == user_id, Expense.created_at >= since)
            .group_by(Expense.category)
        )
        rows = res.all()
        return {category: float(total) for category, total in rows}


async def get_subscription(user_id: int) -> Subscription | None:
    async with AsyncSessionLocal() as session:
        return await session.get(Subscription, user_id)


async def set_subscription(user_id: int, expires_at: dt.datetime | None) -> Subscription:
    async with AsyncSessionLocal() as session:
        sub = await session.get(Subscription, user_id)
        if sub:
            sub.expires_at = expires_at
        else:
            sub = Subscription(user_id=user_id, expires_at=expires_at)
            session.add(sub)
        await session.commit()
        await session.refresh(sub)
        return sub


async def has_active_subscription(user_id: int) -> bool:
    now = dt.datetime.now(dt.timezone.utc)
    async with AsyncSessionLocal() as session:
        sub = await session.get(Subscription, user_id)
        if not sub or not sub.expires_at:
            return False
        return sub.expires_at > now
