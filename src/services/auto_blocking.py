from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from models.entities import User
from models.enums import Role
from patterns.penalty_strategy import PenaltyStrategy
from services.blocking_policy import suggested_block_duration
from services.exceptions import UserNotFoundError
from storage.protocols import IBookRepository, ILoanRepository, IUserRepository
from utils.time_utils import calendar_overdue_days, ensure_aware_utc


class AutoBlockingService:
    """Applies automatic reader suspension after late returns (policy-driven)."""

    def __init__(self, users: IUserRepository) -> None:
        self._users = users

    def maybe_suspend_reader(
        self,
        reader_id: str,
        overdue_days: int,
        penalty: Decimal,
        now: datetime,
    ) -> User | None:
        reader = self._users.get_by_id(reader_id)
        if reader is None:
            raise UserNotFoundError(reader_id)
        if reader.role != Role.READER:
            return None
        duration = suggested_block_duration(overdue_days, penalty)
        if duration is None:
            return None
        when = ensure_aware_utc(now)
        until = when + duration
        if reader.blocked_until is not None and reader.blocked_until > until:
            return reader
        updated = User(
            id=reader.id,
            name=reader.name,
            role=reader.role,
            blocked_until=until,
            max_concurrent_loans=reader.max_concurrent_loans,
        )
        self._users.save(updated)
        return updated

    def enforce_overdue_active_loans(
        self,
        loans: ILoanRepository,
        books: IBookRepository,
        penalty: PenaltyStrategy,
        now: datetime,
    ) -> list[User]:
        """Auto-suspend readers with overdue active loans (UC-07 while books are out)."""
        when = ensure_aware_utc(now)
        worst: dict[str, tuple[int, Decimal]] = {}
        for loan in loans.list_active_all():
            overdue = calendar_overdue_days(loan.due_at, when)
            if overdue <= 0:
                continue
            book = books.get_by_id(loan.book_id)
            if book is None:
                continue
            amount = penalty.calculate(overdue, book.category)
            prev_od, prev_pen = worst.get(loan.user_id, (0, Decimal("0")))
            worst[loan.user_id] = (max(prev_od, overdue), prev_pen + amount)

        blocked: list[User] = []
        for reader_id, (overdue_days, total_penalty) in worst.items():
            updated = self.maybe_suspend_reader(reader_id, overdue_days, total_penalty, when)
            if updated is not None and updated.is_blocked_at(when):
                blocked.append(updated)
        return blocked
