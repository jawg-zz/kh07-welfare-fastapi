"""Database setup with SQLAlchemy async support + query helpers."""
import os
from pathlib import Path
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

DB_PATH = Path(__file__).parent.parent / "db.sqlite3"
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Create all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ── Query helpers ──

async def count_members(db, active_only=False):
    q = select(func.count(Member.id))
    if active_only:
        from app.models import Member
        q = q.where(Member.is_active == True)
    return (await db.execute(q)).scalar() or 0


async def count_causes(db, active_only=True):
    from app.models import ContributionCause
    q = select(func.count(ContributionCause.id))
    if active_only:
        q = q.where(ContributionCause.is_active == True)
    return (await db.execute(q)).scalar() or 0


async def sum_contributions(db, member_id=None, cause_id=None):
    from app.models import Contribution
    q = select(func.coalesce(func.sum(Contribution.amount), 0))
    if member_id is not None:
        q = q.where(Contribution.member_id == member_id)
    if cause_id is not None:
        q = q.where(Contribution.cause_id == cause_id)
    return float((await db.execute(q)).scalar() or 0)


async def count_contributions(db, member_id=None, cause_id=None):
    from app.models import Contribution
    q = select(func.count(Contribution.id))
    if member_id is not None:
        q = q.where(Contribution.member_id == member_id)
    if cause_id is not None:
        q = q.where(Contribution.cause_id == cause_id)
    return (await db.execute(q)).scalar() or 0


async def member_total_and_count(db, member_id):
    """Get total contributed and contribution count for a member in one query."""
    from app.models import Contribution
    r = (await db.execute(
        select(func.coalesce(func.sum(Contribution.amount), 0).label("total"),
               func.count(Contribution.id).label("count"))
        .where(Contribution.member_id == member_id)
    )).one()
    return float(r.total), r.count
