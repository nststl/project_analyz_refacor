from __future__ import annotations

from models.enums import LoanState, Role
from web.context import LibraryContext

LIBRARIAN_ID = "lib-1"


def reader_ids(ctx: LibraryContext) -> frozenset[str]:
    return frozenset(u.id for u in ctx.users.list_all() if u.role == Role.READER)


def book_ids(ctx: LibraryContext) -> frozenset[str]:
    return frozenset(b.id for b in ctx.books.list_all())


def default_reader_id(ctx: LibraryContext) -> str:
    ids = reader_ids(ctx)
    return "reader-1" if "reader-1" in ids else next(iter(ids), "reader-1")


def filter_books(ctx: LibraryContext, search_q: str):
    books = ctx.books.list_all()
    if search_q:
        books = [b for b in books if search_q in b.title.lower()]
    return books


def my_reservations(ctx: LibraryContext, reader_id: str, book_titles: dict[str, str]) -> list[tuple]:
    result: list[tuple] = []
    for b in ctx.books.list_all():
        for res in ctx.reservation_service.queue(b.id):
            if res.user_id == reader_id:
                result.append((res, book_titles.get(b.id, b.id)))
    return result


def loan_history(ctx: LibraryContext, reader_id: str, limit: int = 8):
    history = [
        ln for ln in ctx.loans.list_by_user(reader_id) if ln.state == LoanState.RETURNED
    ]
    history.sort(key=lambda ln: ln.returned_at or ln.due_at, reverse=True)
    return history[:limit]


def reader_rows(ctx: LibraryContext, users, now) -> list[dict]:
    rows: list[dict] = []
    for u in users:
        rows.append(
            {
                "user": u,
                "blocked": u.is_blocked_at(now),
                "active_loans": len(ctx.loan_service.active_loans_for(u.id)),
                "reservations": sum(
                    1
                    for b in ctx.books.list_all()
                    for r in ctx.reservation_service.queue(b.id)
                    if r.user_id == u.id
                ),
            }
        )
    return rows


def build_index_context(
    ctx: LibraryContext,
    *,
    reader_id: str,
    mode: str,
    search_q: str,
) -> dict:
    books = filter_books(ctx, search_q)
    users = [u for u in ctx.users.list_all() if u.role == Role.READER]
    all_books = ctx.books.list_all()
    book_titles = {b.id: b.title for b in all_books}
    reader = ctx.users.get_by_id(reader_id)
    now = ctx.clock.now()
    reservations = my_reservations(ctx, reader_id, book_titles)

    return {
        "books": books,
        "users": users,
        "reader_id": reader_id,
        "reader": reader,
        "librarian": ctx.users.get_by_id(LIBRARIAN_ID),
        "mode": mode,
        "search_q": search_q,
        "active_loans": ctx.loan_service.active_loans_for(reader_id),
        "notifications": ctx.observer.notifications[-5:],
        "blocked": reader.is_blocked_at(now) if reader else False,
        "queues": {b.id: ctx.reservation_service.queue(b.id) for b in all_books},
        "book_titles": book_titles,
        "user_names": {u.id: u.name for u in ctx.users.list_all()},
        "my_reservations": len(reservations),
        "my_reservation_list": reservations,
        "books_available": sum(b.available_copies for b in all_books),
        "loan_history": loan_history(ctx, reader_id),
        "reader_rows": reader_rows(ctx, users, now),
    }
