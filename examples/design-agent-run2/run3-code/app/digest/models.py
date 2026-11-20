"""Row models for the weekly digest tables (see app/migrations/*_create_digest_tables.sql).

Plain dataclasses, no ORM. `as_row()` / `from_row()` map by the column order in the *_COLUMNS tuples,
so any DB-API driver works. Timestamps are timezone-aware datetimes in memory and UTC ISO-8601 text
in the database. No dashboard values, email bodies or recipient addresses are stored (ENG-PLAN).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Optional

SEND_STATUSES = frozenset({"sent", "skipped_empty", "skipped_no_access", "failed"})

SUBSCRIPTION_COLUMNS = (
    "id", "user_id", "dashboard_id", "enabled", "weekday", "hour_local", "tz", "next_send_at",
    "last_sent_at", "consecutive_failures", "unsubscribed_at", "created_at", "updated_at",
)
SEND_COLUMNS = (
    "id", "subscription_id", "period_start", "status", "provider_message_id", "error_code",
    "summary_hash", "created_at",
)


def _require_aware(name: str, value: Optional[datetime]) -> None:
    if value is not None and value.tzinfo is None:
        raise ValueError(f"{name} must be timezone-aware")


def _to_text(value: Optional[datetime]) -> Optional[str]:
    return None if value is None else value.astimezone(timezone.utc).isoformat()


def _from_text(value: Optional[str]) -> Optional[datetime]:
    return None if value is None else datetime.fromisoformat(value)


@dataclass(frozen=True)
class DigestSubscription:
    id: str
    user_id: str
    dashboard_id: str
    enabled: bool
    weekday: int  # 0 = Monday ... 6 = Sunday (Python's datetime.weekday())
    hour_local: int  # 0-23 in `tz`
    tz: str  # IANA name; validated at the API boundary (M2), not here
    next_send_at: datetime
    created_at: datetime
    updated_at: datetime
    last_sent_at: Optional[datetime] = None
    consecutive_failures: int = 0
    unsubscribed_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        for name in ("id", "user_id", "dashboard_id", "tz"):
            if not getattr(self, name):
                raise ValueError(f"{name} is required")
        if not 0 <= self.weekday <= 6:
            raise ValueError("weekday must be 0-6")
        if not 0 <= self.hour_local <= 23:
            raise ValueError("hour_local must be 0-23")
        if self.consecutive_failures < 0:
            raise ValueError("consecutive_failures must be >= 0")
        for name in ("next_send_at", "created_at", "updated_at", "last_sent_at", "unsubscribed_at"):
            _require_aware(name, getattr(self, name))

    def as_row(self) -> tuple:
        return (
            self.id, self.user_id, self.dashboard_id, int(self.enabled), self.weekday, self.hour_local,
            self.tz, _to_text(self.next_send_at), _to_text(self.last_sent_at), self.consecutive_failures,
            _to_text(self.unsubscribed_at), _to_text(self.created_at), _to_text(self.updated_at),
        )

    @classmethod
    def from_row(cls, row) -> "DigestSubscription":
        d = dict(zip(SUBSCRIPTION_COLUMNS, row))
        return cls(
            id=d["id"], user_id=d["user_id"], dashboard_id=d["dashboard_id"], enabled=bool(d["enabled"]),
            weekday=d["weekday"], hour_local=d["hour_local"], tz=d["tz"],
            next_send_at=_from_text(d["next_send_at"]), last_sent_at=_from_text(d["last_sent_at"]),
            consecutive_failures=d["consecutive_failures"], unsubscribed_at=_from_text(d["unsubscribed_at"]),
            created_at=_from_text(d["created_at"]), updated_at=_from_text(d["updated_at"]),
        )


@dataclass(frozen=True)
class DigestSend:
    id: str
    subscription_id: str
    period_start: date
    status: str
    created_at: datetime
    provider_message_id: Optional[str] = None
    error_code: Optional[str] = None
    summary_hash: Optional[str] = None  # hash of the summary for the unchanged check, never the values

    def __post_init__(self) -> None:
        if not self.id or not self.subscription_id:
            raise ValueError("id and subscription_id are required")
        if self.status not in SEND_STATUSES:
            raise ValueError(f"status must be one of {sorted(SEND_STATUSES)}")
        _require_aware("created_at", self.created_at)

    def as_row(self) -> tuple:
        return (
            self.id, self.subscription_id, self.period_start.isoformat(), self.status,
            self.provider_message_id, self.error_code, self.summary_hash, _to_text(self.created_at),
        )

    @classmethod
    def from_row(cls, row) -> "DigestSend":
        d = dict(zip(SEND_COLUMNS, row))
        return cls(
            id=d["id"], subscription_id=d["subscription_id"], period_start=date.fromisoformat(d["period_start"]),
            status=d["status"], provider_message_id=d["provider_message_id"], error_code=d["error_code"],
            summary_hash=d["summary_hash"], created_at=_from_text(d["created_at"]),
        )
