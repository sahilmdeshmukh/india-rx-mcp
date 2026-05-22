from dataclasses import dataclass, field
from datetime import UTC, date, datetime


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass
class Approval:
    approval_id: str
    drug_name: str
    sponsor: str | None
    approval_date: date | None
    indication: str | None
    formulation: str | None
    conditions: str | None
    source_url: str
    scraped_at: datetime = field(default_factory=_utcnow)


@dataclass
class Formulation:
    formulation_id: str
    drug_name: str
    strength: str | None
    form: str | None
    ceiling_price_inr: float | None
    price_effective_date: date | None
    source_url: str
    scraped_at: datetime = field(default_factory=_utcnow)


@dataclass
class PriceChange:
    change_id: int | None             # None for new rows; assigned by SQLite
    formulation_id: str
    old_price_inr: float | None
    new_price_inr: float
    effective_date: date
    reason: str | None
    source_url: str
    scraped_at: datetime = field(default_factory=_utcnow)
