from __future__ import annotations

from models.entities import Book, Loan, Reservation, User
from storage.protocols import IBookRepository, ILoanRepository, IReservationRepository, IUserRepository


class InMemoryUserRepository(IUserRepository):
    def __init__(self) -> None:
        self._by_id: dict[str, User] = {}

    def get_by_id(self, user_id: str) -> User | None:
        return self._by_id.get(user_id)

    def save(self, user: User) -> None:
        self._by_id[user.id] = user

    def list_all(self) -> list[User]:
        return list(self._by_id.values())


class InMemoryBookRepository(IBookRepository):
    def __init__(self) -> None:
        self._by_id: dict[str, Book] = {}

    def get_by_id(self, book_id: str) -> Book | None:
        return self._by_id.get(book_id)

    def save(self, book: Book) -> None:
        self._by_id[book.id] = book

    def list_all(self) -> list[Book]:
        return list(self._by_id.values())


class InMemoryLoanRepository(ILoanRepository):
    def __init__(self) -> None:
        self._by_id: dict[str, Loan] = {}

    def get_by_id(self, loan_id: str) -> Loan | None:
        return self._by_id.get(loan_id)

    def save(self, loan: Loan) -> None:
        self._by_id[loan.id] = loan

    def list_by_user(self, user_id: str) -> list[Loan]:
        return [l for l in self._by_id.values() if l.user_id == user_id]

    def list_by_book(self, book_id: str) -> list[Loan]:
        return [l for l in self._by_id.values() if l.book_id == book_id]

    def list_active_by_user(self, user_id: str) -> list[Loan]:
        from models.enums import LoanState

        return [l for l in self._by_id.values() if l.user_id == user_id and l.state == LoanState.ACTIVE]


class InMemoryReservationRepository(IReservationRepository):
    def __init__(self) -> None:
        self._by_id: dict[str, Reservation] = {}
        self._queues: dict[str, list[str]] = {}
        self._seq = 0

    def next_sequence(self) -> int:
        self._seq += 1
        return self._seq

    def get_by_id(self, reservation_id: str) -> Reservation | None:
        return self._by_id.get(reservation_id)

    def save(self, reservation: Reservation) -> None:
        self._by_id[reservation.id] = reservation
        q = self._queues.setdefault(reservation.book_id, [])
        if reservation.id not in q:
            q.append(reservation.id)
            q.sort(key=lambda rid: self._by_id[rid].sequence)

    def delete(self, reservation_id: str) -> None:
        res = self._by_id.pop(reservation_id, None)
        if res is None:
            return
        q = self._queues.get(res.book_id, [])
        if reservation_id in q:
            q.remove(reservation_id)

    def queue_for_book(self, book_id: str) -> list[Reservation]:
        return [self._by_id[rid] for rid in self._queues.get(book_id, []) if rid in self._by_id]

    def has_user_pending(self, user_id: str, book_id: str) -> bool:
        return any(r.user_id == user_id for r in self.queue_for_book(book_id))
