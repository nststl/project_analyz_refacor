from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from models.enums import BookCategory, LoanState, Role


@dataclass(frozen=True, slots=True)
class User:
    id: str
    name: str
    role: Role
    blocked_until: datetime | None = None
    max_concurrent_loans: int = 3

    def is_blocked_at(self, when: datetime) -> bool:
        return self.blocked_until is not None and when < self.blocked_until


@dataclass(slots=True)
class Book:
    id: str
    title: str
    category: BookCategory
    total_copies: int
    available_copies: int

    def __post_init__(self) -> None:
        if self.total_copies < 0 or self.available_copies < 0:
            raise ValueError("copy counts must be non-negative")
        if self.available_copies > self.total_copies:
            raise ValueError("available cannot exceed total")


@dataclass(slots=True)
class Loan:
    id: str
    user_id: str
    book_id: str
    borrowed_at: datetime
    due_at: datetime
    state: LoanState = LoanState.ACTIVE
    returned_at: datetime | None = None
    penalty_amount: Decimal = field(default_factory=lambda: Decimal("0"))


@dataclass(frozen=True, slots=True)
class Reservation:
    id: str
    user_id: str
    book_id: str
    sequence: int
