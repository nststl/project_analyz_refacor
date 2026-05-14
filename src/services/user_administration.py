from __future__ import annotations

from datetime import datetime

from models.entities import User
from models.enums import Role
from services.exceptions import LibrarianRoleRequiredError, ReaderRoleRequiredError, UserNotFoundError
from storage.protocols import IUserRepository
from utils.time_utils import ensure_aware_utc


class UserAdministrationService:
    """Librarian-driven reader blocking."""

    def __init__(self, users: IUserRepository) -> None:
        self._users = users

    def block_reader_until(self, librarian_id: str, reader_id: str, until: datetime) -> User:
        self._require_librarian(librarian_id)
        reader = self._users.get_by_id(reader_id)
        if reader is None:
            raise UserNotFoundError(reader_id)
        if reader.role != Role.READER:
            raise ReaderRoleRequiredError("target must be a reader")
        updated = User(
            id=reader.id,
            name=reader.name,
            role=reader.role,
            blocked_until=ensure_aware_utc(until),
            max_concurrent_loans=reader.max_concurrent_loans,
        )
        self._users.save(updated)
        return updated

    def unblock_reader(self, librarian_id: str, reader_id: str) -> User:
        self._require_librarian(librarian_id)
        reader = self._users.get_by_id(reader_id)
        if reader is None:
            raise UserNotFoundError(reader_id)
        updated = User(
            id=reader.id,
            name=reader.name,
            role=reader.role,
            blocked_until=None,
            max_concurrent_loans=reader.max_concurrent_loans,
        )
        self._users.save(updated)
        return updated

    def _require_librarian(self, user_id: str) -> User:
        u = self._users.get_by_id(user_id)
        if u is None:
            raise UserNotFoundError(user_id)
        if u.role != Role.LIBRARIAN:
            raise LibrarianRoleRequiredError("librarian role required")
        return u
