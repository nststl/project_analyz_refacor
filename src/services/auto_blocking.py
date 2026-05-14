from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from models.entities import User
from models.enums import Role
from services.blocking_policy import suggested_block_duration
from services.exceptions import UserNotFoundError
from storage.protocols import IUserRepository
from utils.time_utils import ensure_aware_utc


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
