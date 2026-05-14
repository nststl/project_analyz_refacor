from __future__ import annotations

from datetime import datetime, timezone


def ensure_aware_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def calendar_overdue_days(due_at: datetime, returned_at: datetime) -> int:
    """Whole calendar days after due date (due date itself is not overdue)."""
    due = ensure_aware_utc(due_at).date()
    ret = ensure_aware_utc(returned_at).date()
    if ret <= due:
        return 0
    return (ret - due).days
