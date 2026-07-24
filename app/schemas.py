"""Pydantic schemas for request/response validation."""
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


# ── Member ──
class MemberBase(BaseModel):
    name: str
    phone_number: str = ""
    is_active: bool = True
    notes: str = ""


class MemberCreate(MemberBase):
    pass


class MemberUpdate(BaseModel):
    name: str | None = None
    phone_number: str | None = None
    is_active: bool | None = None
    notes: str | None = None


class MemberOut(MemberBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    member_number: int
    total_contributed: Decimal = Decimal("0")
    contribution_count: int = 0
    causes_supported: int = 0


class MemberListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    member_number: int
    name: str
    phone_number: str = ""
    is_active: bool
    total_contributed: float = 0
    contribution_count: int = 0


# ── ContributionCause ──
class CauseBase(BaseModel):
    name: str
    description: str = ""
    date_occurred: date | None = None
    target_amount: Decimal | None = None
    is_active: bool = True


class CauseCreate(CauseBase):
    pass


class CauseOut(CauseBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    total_collected: Decimal = Decimal("0")
    member_count: int = 0
    progress_percent: float | None = None


# ── Contribution ──
class ContributionBase(BaseModel):
    amount: Decimal
    date_paid: date | None = None
    notes: str = ""


class ContributionCreate(ContributionBase):
    member_id: int
    cause_id: int


class ContributionOut(ContributionBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    member_id: int
    cause_id: int
    member_name: str = ""
    cause_name: str = ""


# ── Dashboard ──
class DashboardStats(BaseModel):
    total_members: int
    active_members: int
    total_causes: int
    total_contributions: int
    total_collected: float
    avg_per_member: float
