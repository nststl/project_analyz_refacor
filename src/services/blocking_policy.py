from __future__ import annotations

from datetime import timedelta
from decimal import Decimal


def suggested_block_duration(overdue_days: int, penalty: Decimal) -> timedelta | None:
    """Business rule: severe lateness or high debt triggers temporary suspension."""
    if overdue_days <= 0 and penalty <= 0:
        return None
    if penalty >= Decimal("500") or overdue_days >= 45:
        return timedelta(days=30)
    if penalty >= Decimal("200") or overdue_days >= 21:
        return timedelta(days=14)
    if overdue_days >= 7:
        return timedelta(days=3)
    return None
