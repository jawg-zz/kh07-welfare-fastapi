"""SQLAlchemy models for KH07 Welfare."""
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import String, Integer, Date, DateTime, Text, Boolean, ForeignKey, func
from sqlalchemy.types import DECIMAL as SQLDecimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class User(Base):
    """System users with role-based access."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="admin")  # admin | viewer
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"{self.username} ({self.role})"


class Member(Base):
    __tablename__ = "members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    member_number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    phone_number: Mapped[str] = mapped_column(String(20), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    joined_date: Mapped[date] = mapped_column(Date, default=date.today)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    contributions: Mapped[list["Contribution"]] = relationship(back_populates="member", cascade="all, delete-orphan")

    def __repr__(self):
        return f"#{self.member_number} {self.name}"


class ContributionCause(Base):
    __tablename__ = "contribution_causes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(300), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    date_occurred: Mapped[date | None] = mapped_column(Date, nullable=True)
    target_amount: Mapped[Decimal | None] = mapped_column(SQLDecimal(12, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    contributions: Mapped[list["Contribution"]] = relationship(back_populates="cause", cascade="all, delete-orphan")
    disbursements: Mapped[list["Disbursement"]] = relationship(back_populates="cause", cascade="all, delete-orphan")

    def __repr__(self):
        return self.name


class Contribution(Base):
    __tablename__ = "contributions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), nullable=False, index=True)
    cause_id: Mapped[int] = mapped_column(ForeignKey("contribution_causes.id", ondelete="CASCADE"), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(SQLDecimal(10, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(20), default="cash", index=True)
    transaction_ref: Mapped[str] = mapped_column(String(100), default="")
    date_paid: Mapped[date] = mapped_column(Date, nullable=False, default=date.today, index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    member: Mapped["Member"] = relationship(back_populates="contributions")
    cause: Mapped["ContributionCause"] = relationship(back_populates="contributions")

    def __repr__(self):
        return f"{self.member.name} → {self.cause.name}: KES {self.amount}"


class Disbursement(Base):
    __tablename__ = "disbursements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cause_id: Mapped[int] = mapped_column(ForeignKey("contribution_causes.id", ondelete="CASCADE"), nullable=False, index=True)
    beneficiary_name: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[Decimal] = mapped_column(SQLDecimal(10, 2), nullable=False)
    date_disbursed: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    cause: Mapped["ContributionCause"] = relationship(back_populates="disbursements")

    def __repr__(self):
        return f"Disburse KES {self.amount} to {self.beneficiary_name}"
