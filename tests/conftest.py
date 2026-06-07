from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Callable

import pytest
from decimal import Decimal

from models.entities import Book, User
from models.enums import BookCategory, Role
from patterns.observer import BookAvailabilitySubject
from patterns.penalty_strategy import LinearPenaltyStrategy
from services.auto_blocking import AutoBlockingService
from services.loan_service import LoanService, SequentialIdGenerator
from services.reservation_service import ReservationQueueObserver, ReservationService
from services.user_administration import UserAdministrationService
from storage.in_memory import (
    InMemoryBookRepository,
    InMemoryLoanRepository,
    InMemoryReservationRepository,
    InMemoryUserRepository,
)
from utils.time_utils import ensure_aware_utc

os.environ.setdefault("FLASK_TEST_SECRET_KEY", "0" * 64)


class FrozenClock:
    def __init__(self, t: datetime) -> None:
        self._t = ensure_aware_utc(t)

    def now(self) -> datetime:
        return self._t

    def set(self, t: datetime) -> None:
        self._t = ensure_aware_utc(t)


@pytest.fixture
def t0() -> datetime:
    return datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def frozen_clock(t0: datetime) -> FrozenClock:
    return FrozenClock(t0)


@pytest.fixture
def repos() -> tuple[
    InMemoryUserRepository,
    InMemoryBookRepository,
    InMemoryLoanRepository,
    InMemoryReservationRepository,
]:
    return (
        InMemoryUserRepository(),
        InMemoryBookRepository(),
        InMemoryLoanRepository(),
        InMemoryReservationRepository(),
    )


@pytest.fixture
def make_system(
    repos: tuple,
    t0: datetime,
) -> Callable[..., tuple[LoanService, ReservationService, ReservationQueueObserver, AutoBlockingService, UserAdministrationService, FrozenClock]]:
    users, books, loans, reservations = repos

    def _make(
        *,
        penalty_per_day: Decimal = Decimal("10"),
        loan_days: int = 14,
    ) -> tuple[
        LoanService,
        ReservationService,
        ReservationQueueObserver,
        AutoBlockingService,
        UserAdministrationService,
        FrozenClock,
    ]:
        clock = FrozenClock(t0)
        subject = BookAvailabilitySubject()
        ids = SequentialIdGenerator()
        penalty = LinearPenaltyStrategy(penalty_per_day)
        observer = ReservationQueueObserver(reservations)
        subject.attach(observer)
        loan_svc = LoanService(
            users=users,
            books=books,
            loans=loans,
            penalty=penalty,
            clock=clock,
            ids=ids,
            availability=subject,
            default_loan_days=loan_days,
        )
        res_svc = ReservationService(users=users, books=books, reservations=reservations, ids=ids)
        auto_block = AutoBlockingService(users=users)
        admin = UserAdministrationService(users=users)
        return loan_svc, res_svc, observer, auto_block, admin, clock

    return _make


@pytest.fixture
def sample_reader(repos, t0) -> User:
    users, *_ = repos
    u = User(id="reader-1", name="Ann Reader", role=Role.READER, blocked_until=None, max_concurrent_loans=3)
    users.save(u)
    return u


@pytest.fixture
def sample_librarian(repos) -> User:
    users, *_ = repos
    u = User(id="lib-1", name="Bob Staff", role=Role.LIBRARIAN)
    users.save(u)
    return u


@pytest.fixture
def sample_book(repos) -> Book:
    _, books, *_ = repos
    b = Book(id="book-1", title="Python 101", category=BookCategory.STANDARD, total_copies=2, available_copies=2)
    books.save(b)
    return b
