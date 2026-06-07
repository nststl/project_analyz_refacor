from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from flask import flash

from services.exceptions import DomainError
from utils.time_utils import calendar_overdue_days
from web.context import LibraryContext
from web.index_data import LIBRARIAN_ID
from web.security import safe_error_message
from web.simulation import advance_simulation_days, apply_penalty_strategy, log_event


def log_borrow(ctx: LibraryContext, reader_id: str, book_id: str) -> None:
    loan = ctx.loan_service.borrow(reader_id, book_id)
    book = ctx.books.get_by_id(book_id)
    title = book.title if book else book_id
    log_event(ctx, f"UC-01 {reader_id} взяв «{title}» (до {loan.due_at.date()})")


def log_return(ctx: LibraryContext, loan_id: str) -> None:
    notif_before = len(ctx.observer.notifications)
    loan = ctx.loan_service.return_loan(loan_id)
    if loan.returned_at is not None and loan.penalty_amount > 0:
        overdue = calendar_overdue_days(loan.due_at, loan.returned_at)
        ctx.auto_blocking.maybe_suspend_reader(
            loan.user_id, overdue, loan.penalty_amount, ctx.clock.now()
        )
        log_event(
            ctx,
            f"UC-03 Повернення з штрафом {loan.penalty_amount} грн (+{overdue} дн.)",
        )
    else:
        log_event(ctx, "UC-02 Повернення вчасно, штраф 0 грн")
    if len(ctx.observer.notifications) > notif_before:
        last = ctx.observer.notifications[-1]
        log_event(ctx, f"UC-05 Observer: книга {last[0]} доступна для {last[1]}")


def flash_advance_time(ctx: LibraryContext, days: int) -> None:
    try:
        blocked = advance_simulation_days(ctx, days)
    except (ValueError, DomainError):
        flash("Помилка операції.", "error")
        return
    if blocked:
        flash(
            f"Час +{days} дн. Автоблокування (UC-07): {len(blocked)} читач(ів).",
            "success",
        )
    else:
        flash(f"Час симуляції переведено вперед на {days} дн.", "success")


def apply_and_flash_penalty_strategy(ctx: LibraryContext, kind: str, rate: Decimal) -> None:
    label = apply_penalty_strategy(ctx, kind, rate)
    flash(f"Стратегія штрафів: {label}", "success")


def block_reader_admin(ctx: LibraryContext, target_id: str, days: int) -> None:
    until = ctx.clock.now() + timedelta(days=days)
    ctx.admin_service.block_reader_until(LIBRARIAN_ID, target_id, until)
    log_event(ctx, f"UC-06 Блокування {target_id} на {days} дн.")
    flash("Читача заблоковано.", "success")


def block_reader_admin_safe(ctx: LibraryContext, target_id: str, days: int) -> None:
    try:
        block_reader_admin(ctx, target_id, days)
    except DomainError as exc:
        flash(safe_error_message(exc), "error")
