from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@runtime_checkable
class BookReturnObserver(Protocol):
    def on_book_available(
        self, book_id: str, available_copies: int
    ) -> tuple[str, str, int] | None: ...


@dataclass
class BookAvailabilitySubject:
    """Observer subject: notifies subscribers when a book becomes available."""

    _observers: list[BookReturnObserver] = field(default_factory=list)

    def attach(self, observer: BookReturnObserver) -> None:
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer: BookReturnObserver) -> None:
        if observer in self._observers:
            self._observers.remove(observer)

    def notify(self, book_id: str, available_copies: int) -> list[tuple[str, str, int]]:
        events: list[tuple[str, str, int]] = []
        for o in self._observers[:]:
            event = o.on_book_available(book_id, available_copies)
            if event is not None:
                events.append(event)
        return events
