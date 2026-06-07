from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Protocol, runtime_checkable

from models.entities import Book, Loan, User
from models.enums import BookCategory, LoanState, Role
from patterns.observer import BookAvailabilitySubject
from patterns.penalty_strategy import PenaltyStrategy
from services.exceptions import (
    BookNotFoundError,
    InsufficientCopiesError,
    InvalidLoanStateError,
    LoanLimitExceededError,
    LoanNotFoundError,
    ReaderRoleRequiredError,
    ReferenceBookNotLoanableError,
    UserBlockedError,
    UserNotFoundError,
)
from storage.protocols import IBookRepository, ILoanRepository, IUserRepository
from utils.time_utils import calendar_overdue_days, ensure_aware_utc


@runtime_checkable
class Clock(Protocol):
    def now(self) -> datetime: ...


@runtime_checkable
class IdGenerator(Protocol):
    def new_id(self, prefix: str) -> str: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class SimulatedClock:
    """Adjustable clock for in-browser simulation (time travel for overdue tests)."""

    def __init__(self, start: datetime | None = None) -> None:
        self._now = ensure_aware_utc(start or datetime.now(timezone.utc))

    def now(self) -> datetime:
        return self._now

    def advance_days(self, days: int) -> datetime:
        if days <= 0:
            raise ValueError("days must be positive")
        self._now = self._now + timedelta(days=days)
        return self._now

    def set(self, moment: datetime) -> None:
        self._now = ensure_aware_utc(moment)


class UuidIdGenerator:
    def new_id(self, prefix: str) -> str:
        import uuid

        return f"{prefix}-{uuid.uuid4().hex[:12]}"


class SequentialIdGenerator:
    def __init__(self) -> None:
        self._n = 0

    def new_id(self, prefix: str) -> str:
        self._n += 1
        return f"{prefix}-{self._n}"


class LoanService:
    """Borrow / return with penalty calculation and availability notifications."""

    def __init__(
        self,
        users: IUserRepository,
        books: IBookRepository,
        loans: ILoanRepository,
        penalty: PenaltyStrategy,
        clock: Clock,
        ids: IdGenerator,
        availability: BookAvailabilitySubject,
        default_loan_days: int = 14,
    ) -> None:
        self._users = users
        self._books = books
        self._loans = loans
        self._penalty = penalty
        self._clock = clock
        self._ids = ids
        self._availability = availability
        self._default_loan_days = default_loan_days

    def borrow(self, user_id: str, book_id: str, loan_days: int | None = None) -> Loan:
        user = self._require_reader(user_id)
        when = ensure_aware_utc(self._clock.now())
        if user.is_blocked_at(when):
            raise UserBlockedError("reader is blocked")
        book = self._books.get_by_id(book_id)
        if book is None:
            raise BookNotFoundError(book_id)
        if book.category == BookCategory.REFERENCE:
            raise ReferenceBookNotLoanableError("reference titles are in-library only")
        if book.available_copies <= 0:
            raise InsufficientCopiesError("no copies available")
        active = self._loans.list_active_by_user(user_id)
        if len(active) >= user.max_concurrent_loans:
            raise LoanLimitExceededError("too many active loans")

        days = self._default_loan_days if loan_days is None else loan_days
        if days <= 0:
            raise ValueError("loan_days must be positive")

        borrowed_at = when
        due_at = borrowed_at + timedelta(days=days)
        loan = Loan(
            id=self._ids.new_id("loan"),
            user_id=user_id,
            book_id=book_id,
            borrowed_at=borrowed_at,
            due_at=due_at,
            state=LoanState.ACTIVE,
        )
        self._loans.save(loan)
        self._decrement_book(book)
        return loan

    def return_loan(self, loan_id: str, returned_at: datetime | None = None) -> Loan:
        loan, _events = self.return_loan_with_events(loan_id, returned_at)
        return loan

    def return_loan_with_events(
        self, loan_id: str, returned_at: datetime | None = None
    ) -> tuple[Loan, list[tuple[str, str, int]]]:
        loan = self._loans.get_by_id(loan_id)
        if loan is None:
            raise LoanNotFoundError(loan_id)
        if loan.state != LoanState.ACTIVE:
            raise InvalidLoanStateError("loan is not active")
        ret = ensure_aware_utc(returned_at or self._clock.now())
        book = self._books.get_by_id(loan.book_id)
        if book is None:
            raise BookNotFoundError(loan.book_id)

        overdue = calendar_overdue_days(loan.due_at, ret)
        penalty = self._penalty.calculate(overdue, book.category)

        loan.state = LoanState.RETURNED
        loan.returned_at = ret
        loan.penalty_amount = penalty
        self._loans.save(loan)

        self._increment_book(book)
        events = self._availability.notify(book.id, book.available_copies)
        return loan, events

    def active_loans_for(self, user_id: str) -> list[Loan]:
        return self._loans.list_active_by_user(user_id)

    def estimated_penalty(self, loan: Loan, as_of: datetime | None = None) -> Decimal:
        when = ensure_aware_utc(as_of or self._clock.now())
        book = self._books.get_by_id(loan.book_id)
        if book is None:
            return Decimal("0")
        overdue = calendar_overdue_days(loan.due_at, when)
        return self._penalty.calculate(overdue, book.category)

    def set_penalty_strategy(self, strategy: PenaltyStrategy) -> None:
        self._penalty = strategy

    @property
    def penalty_strategy(self) -> PenaltyStrategy:
        return self._penalty

    def _require_reader(self, user_id: str) -> User:
        u = self._users.get_by_id(user_id)
        if u is None:
            raise UserNotFoundError(user_id)
        if u.role != Role.READER:
            raise ReaderRoleRequiredError("only readers may borrow")
        return u

    def _decrement_book(self, book: Book) -> None:
        if book.available_copies <= 0:
            raise InsufficientCopiesError("no copies available")
        book.available_copies -= 1
        self._books.save(book)

    def _increment_book(self, book: Book) -> None:
        book.available_copies = min(book.total_copies, book.available_copies + 1)
        self._books.save(book)

