from __future__ import annotations

from datetime import timedelta

from flask import Flask, flash, redirect, render_template, request, url_for

from services.exceptions import DomainError
from utils.time_utils import calendar_overdue_days
from web.context import LibraryContext
from web.index_data import (
    LIBRARIAN_ID,
    book_ids,
    build_index_context,
    default_reader_id,
    reader_ids,
)
from web.security import (
    clamp_block_days,
    pick_book_id,
    pick_mode,
    pick_reader_id,
    safe_error_message,
    sanitize_search_query,
)


def register_routes(app: Flask, ctx: LibraryContext) -> None:
    def redirect_back(reader_id: str, mode: str = "reader", **extra: str) -> redirect:
        safe_reader = pick_reader_id(reader_id, reader_ids(ctx), default_reader_id(ctx))
        safe_mode = pick_mode(mode)
        safe_extra = {k: v for k, v in extra.items() if k == "q" and v}
        if "q" in safe_extra:
            safe_extra["q"] = sanitize_search_query(safe_extra["q"])
        return redirect(url_for("index", reader_id=safe_reader, mode=safe_mode, **safe_extra))

    def form_reader_id() -> str:
        return pick_reader_id(
            request.form.get("reader_id", default_reader_id(ctx)),
            reader_ids(ctx),
            default_reader_id(ctx),
        )

    def form_mode() -> str:
        return pick_mode(request.form.get("mode", "reader"))

    def require_librarian_mode() -> bool:
        if request.form.get("mode") != "librarian":
            flash("Ця дія доступна лише в режимі бібліотекаря.", "error")
            return False
        return True

    @app.get("/")
    def index():
        mode = pick_mode(request.args.get("mode", "reader"))
        reader_id = pick_reader_id(
            request.args.get("reader_id", default_reader_id(ctx)),
            reader_ids(ctx),
            default_reader_id(ctx),
        )
        search_q = sanitize_search_query(request.args.get("q", ""))
        return render_template(
            "index.html",
            **build_index_context(ctx, reader_id=reader_id, mode=mode, search_q=search_q),
        )

    @app.post("/borrow")
    def borrow():
        reader_id = form_reader_id()
        mode = form_mode()
        book_id = pick_book_id(request.form.get("book_id", ""), book_ids(ctx))
        try:
            ctx.loan_service.borrow(reader_id, book_id)
            flash("Книгу видано. Перевірте розділ «Мої позики».", "success")
        except DomainError as exc:
            flash(safe_error_message(exc), "error")
        return redirect_back(reader_id, mode)

    @app.post("/return")
    def return_loan():
        reader_id = form_reader_id()
        mode = form_mode()
        loan_id = request.form.get("loan_id", "")
        try:
            loan = ctx.loan_service.return_loan(loan_id)
            overdue = 0
            if loan.returned_at is not None:
                overdue = calendar_overdue_days(loan.due_at, loan.returned_at)
            flash("Книгу повернено.", "success")
            if loan.penalty_amount > 0:
                ctx.auto_blocking.maybe_suspend_reader(
                    loan.user_id,
                    overdue,
                    loan.penalty_amount,
                    ctx.clock.now(),
                )
        except DomainError as exc:
            flash(safe_error_message(exc), "error")
        return redirect_back(reader_id, mode)

    @app.post("/reserve")
    def reserve():
        reader_id = form_reader_id()
        mode = form_mode()
        book_id = pick_book_id(request.form.get("book_id", ""), book_ids(ctx))
        try:
            ctx.reservation_service.enqueue(reader_id, book_id)
            flash("Додано до черги резерву.", "success")
        except DomainError as exc:
            flash(safe_error_message(exc), "error")
        return redirect_back(reader_id, mode)

    @app.post("/cancel-reservation")
    def cancel_reservation():
        reader_id = form_reader_id()
        mode = form_mode()
        reservation_id = request.form.get("reservation_id", "")
        try:
            ctx.reservation_service.cancel(reader_id, reservation_id)
            flash("Резерв скасовано.", "success")
        except DomainError as exc:
            flash(safe_error_message(exc), "error")
        return redirect_back(reader_id, mode)

    @app.post("/block")
    def block_reader():
        if not require_librarian_mode():
            return redirect_back(form_reader_id(), "reader")
        target_id = pick_reader_id(
            request.form.get("target_reader_id", ""),
            reader_ids(ctx),
            default_reader_id(ctx),
        )
        days = clamp_block_days(request.form.get("days", "7"))
        try:
            until = ctx.clock.now() + timedelta(days=days)
            ctx.admin_service.block_reader_until(LIBRARIAN_ID, target_id, until)
            flash("Читача заблоковано.", "success")
        except DomainError as exc:
            flash(safe_error_message(exc), "error")
        return redirect_back(form_reader_id(), "librarian")

    @app.post("/unblock")
    def unblock_reader():
        if not require_librarian_mode():
            return redirect_back(form_reader_id(), "reader")
        target_id = pick_reader_id(
            request.form.get("target_reader_id", ""),
            reader_ids(ctx),
            default_reader_id(ctx),
        )
        try:
            ctx.admin_service.unblock_reader(LIBRARIAN_ID, target_id)
            flash("Читача розблоковано.", "success")
        except DomainError as exc:
            flash(safe_error_message(exc), "error")
        return redirect_back(form_reader_id(), "librarian")
