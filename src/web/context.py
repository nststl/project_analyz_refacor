from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from models.entities import Book, User
from models.enums import BookCategory, Role
from patterns.observer import BookAvailabilitySubject
from patterns.penalty_strategy import LinearPenaltyStrategy
from services.auto_blocking import AutoBlockingService
from services.loan_service import LoanService, SequentialIdGenerator, SimulatedClock
from services.reservation_service import ReservationQueueObserver, ReservationService
from services.user_administration import UserAdministrationService
from storage.in_memory import (
    InMemoryBookRepository,
    InMemoryLoanRepository,
    InMemoryReservationRepository,
    InMemoryUserRepository,
)


@dataclass
class LibraryContext:
    users: InMemoryUserRepository
    books: InMemoryBookRepository
    loans: InMemoryLoanRepository
    reservations: InMemoryReservationRepository
    clock: SimulatedClock
    loan_service: LoanService
    reservation_service: ReservationService
    admin_service: UserAdministrationService
    auto_blocking: AutoBlockingService
    observer: ReservationQueueObserver
    penalty_kind: str = "linear"
    penalty_rate: Decimal = field(default_factory=lambda: Decimal("10"))
    event_log: list[str] = field(default_factory=list)


def build_library_context(*, seed: bool = True) -> LibraryContext:
    users = InMemoryUserRepository()
    books = InMemoryBookRepository()
    loans = InMemoryLoanRepository()
    reservations = InMemoryReservationRepository()

    subject = BookAvailabilitySubject()
    observer = ReservationQueueObserver(reservations)
    subject.attach(observer)

    clock = SimulatedClock(datetime(2026, 6, 5, 12, 0, tzinfo=timezone.utc))
    penalty_rate = Decimal("10")
    loan_service = LoanService(
        users=users,
        books=books,
        loans=loans,
        penalty=LinearPenaltyStrategy(penalty_rate),
        clock=clock,
        ids=SequentialIdGenerator(),
        availability=subject,
        default_loan_days=14,
    )
    reservation_service = ReservationService(
        users=users,
        books=books,
        reservations=reservations,
        ids=SequentialIdGenerator(),
    )
    admin_service = UserAdministrationService(users=users)
    auto_blocking = AutoBlockingService(users=users)

    ctx = LibraryContext(
        users=users,
        books=books,
        loans=loans,
        reservations=reservations,
        clock=clock,
        loan_service=loan_service,
        reservation_service=reservation_service,
        admin_service=admin_service,
        auto_blocking=auto_blocking,
        observer=observer,
        penalty_kind="linear",
        penalty_rate=penalty_rate,
    )
    if seed:
        _seed_demo_data(ctx)
    return ctx


def _seed_demo_data(ctx: LibraryContext) -> None:
    ctx.users.save(User("reader-1", "Ann Reader", Role.READER, None, 2))
    ctx.users.save(User("reader-2", "Богдан Книголюб", Role.READER, None, 2))
    ctx.users.save(User("lib-1", "Bob Librarian", Role.LIBRARIAN))
    ctx.books.save(Book("b1", "Python для початківців", BookCategory.STANDARD, 3, 3))
    ctx.books.save(Book("b2", "Clean Code", BookCategory.STANDARD, 1, 0))
    ctx.books.save(Book("b3", "Велика Британська Енциклопедія", BookCategory.REFERENCE, 1, 1))
    ctx.books.save(Book("b4", "Паттерни проектування GoF", BookCategory.RARE, 2, 2))
    ctx.books.save(Book("b5", "Refactoring", BookCategory.STANDARD, 2, 1))
    ctx.books.save(Book("b6", "Міфічний місяць", BookCategory.STANDARD, 1, 1))
    ctx.books.save(Book("b7", "Довідник ISO", BookCategory.REFERENCE, 1, 1))
