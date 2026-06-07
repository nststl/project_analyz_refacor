from __future__ import annotations

from models.entities import Reservation
from models.enums import Role
from patterns.observer import BookReturnObserver
from services.exceptions import (
    BookNotFoundError,
    DuplicateReservationError,
    ReaderRoleRequiredError,
    ReservationAccessDeniedError,
    ReservationNotFoundError,
    UserNotFoundError,
)
from services.loan_service import IdGenerator
from storage.protocols import IBookRepository, IReservationRepository, IUserRepository


class ReservationService:
    """FIFO queue per book; readers may enqueue when out of stock."""

    def __init__(
        self,
        users: IUserRepository,
        books: IBookRepository,
        reservations: IReservationRepository,
        ids: IdGenerator,
    ) -> None:
        self._users = users
        self._books = books
        self._res = reservations
        self._ids = ids

    def enqueue(self, reader_id: str, book_id: str) -> Reservation:
        reader = self._users.get_by_id(reader_id)
        if reader is None:
            raise UserNotFoundError(reader_id)
        if reader.role != Role.READER:
            raise ReaderRoleRequiredError("only readers reserve")
        book = self._books.get_by_id(book_id)
        if book is None:
            raise BookNotFoundError(book_id)
        if self._res.has_user_pending(reader_id, book_id):
            raise DuplicateReservationError("already queued for this book")
        r = Reservation(
            id=self._ids.new_id("res"),
            user_id=reader_id,
            book_id=book_id,
            sequence=self._res.next_sequence(),
        )
        self._res.save(r)
        return r

    def cancel(self, reader_id: str, reservation_id: str) -> None:
        r = self._res.get_by_id(reservation_id)
        if r is None:
            raise ReservationNotFoundError(reservation_id)
        if r.user_id != reader_id:
            raise ReservationAccessDeniedError("not owner of reservation")
        self._res.delete(reservation_id)

    def queue(self, book_id: str) -> list[Reservation]:
        return self._res.queue_for_book(book_id)


class ReservationQueueObserver(BookReturnObserver):
    """Observer: records the next reader in queue when a copy becomes available."""

    def __init__(self, reservations: IReservationRepository) -> None:
        self._res = reservations
        self.notifications: list[tuple[str, str, int]] = []

    def on_book_available(
        self, book_id: str, available_copies: int
    ) -> tuple[str, str, int] | None:
        if available_copies <= 0:
            return None
        q = self._res.queue_for_book(book_id)
        if not q:
            return None
        head = q[0]
        event = (book_id, head.user_id, available_copies)
        self.notifications.append(event)
        return event
