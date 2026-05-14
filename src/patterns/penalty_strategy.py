from __future__ import annotations

from decimal import Decimal
from typing import Protocol, runtime_checkable

from models.enums import BookCategory


@runtime_checkable
class PenaltyStrategy(Protocol):
    def calculate(self, overdue_days: int, category: BookCategory) -> Decimal: ...


class LinearPenaltyStrategy:
    """Fixed amount per overdue calendar day, with category multiplier."""

    def __init__(self, amount_per_day: Decimal, rare_multiplier: Decimal = Decimal("2")) -> None:
        self._per_day = amount_per_day
        self._rare = rare_multiplier

    def calculate(self, overdue_days: int, category: BookCategory) -> Decimal:
        if overdue_days <= 0:
            return Decimal("0")
        mult = self._rare if category == BookCategory.RARE else Decimal("1")
        if category == BookCategory.REFERENCE:
            mult *= Decimal("1.5")
        return self._per_day * Decimal(overdue_days) * mult


class TieredPenaltyStrategy:
    """Higher rate after a threshold of overdue days (Strategy variant)."""

    def __init__(
        self,
        low_rate: Decimal,
        high_rate: Decimal,
        threshold_days: int = 7,
    ) -> None:
        self._low = low_rate
        self._high = high_rate
        self._thr = threshold_days

    def calculate(self, overdue_days: int, category: BookCategory) -> Decimal:
        if overdue_days <= 0:
            return Decimal("0")
        low_days = min(overdue_days, self._thr)
        high_days = max(0, overdue_days - self._thr)
        base = self._low * Decimal(low_days) + self._high * Decimal(high_days)
        if category == BookCategory.RARE:
            base *= Decimal("2")
        return base
