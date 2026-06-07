from __future__ import annotations

from datetime import timedelta

from flask import Flask, flash, redirect, render_template, request

from utils.time_utils import calendar_overdue_days
from web.context import LibraryContext
from web.index_data import (
    LIBRARIAN_ID,
    book_ids,
    build_index_context,
    default_reader_id,
    reader_ids,
)
from web.route_helpers import RouteHelpers
from web.security import (
    clamp_block_days,
    pick_book_id,
    pick_mode,
    pick_reader_id,
    safe_error_message,
    sanitize_search_query,
)


def register_routes(app: Flask, ctx: LibraryContext) -> None:
    h = RouteHelpers(ctx)

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
        rid, mode = h.form_reader_id(), h.form_mode()
        bid = pick_book_id(request.form.get("book_id", ""), book_ids(ctx))
        return h.run_action(
            lambda: ctx.loan_service.borrow(rid, bid),
            "Книгу видано. Перевірте розділ «Мої позики».",
            rid,
            mode,
        )

    @app.post("/return")
    def return_loan():
        rid, mode = h.form_reader_id(), h.form_mode()
        loan_id = request.form.get("loan_id", "")

        def _return() -> None:
            loan = ctx.loan_service.return_loan(loan_id)
            if loan.returned_at is not None and loan.penalty_amount > 0:
                overdue = calendar_overdue_days(loan.due_at, loan.returned_at)
                ctx.auto_blocking.maybe_suspend_reader(
                    loan.user_id, overdue, loan.penalty_amount, ctx.clock.now()
                )

        return h.run_action(_return, "Книгу повернено.", rid, mode)

    @app.post("/reserve")
    def reserve():
        rid, mode = h.form_reader_id(), h.form_mode()
        bid = pick_book_id(request.form.get("book_id", ""), book_ids(ctx))
        return h.run_action(
            lambda: ctx.reservation_service.enqueue(rid, bid),
            "Додано до черги резерву.",
            rid,
            mode,
        )

    @app.post("/cancel-reservation")
    def cancel_reservation():
        rid, mode = h.form_reader_id(), h.form_mode()
        res_id = request.form.get("reservation_id", "")
        return h.run_action(
            lambda: ctx.reservation_service.cancel(rid, res_id),
            "Резерв скасовано.",
            rid,
            mode,
        )

    @app.post("/block")
    def block_reader():
        if not h.require_librarian_mode():
            return h.redirect_back(h.form_reader_id(), "reader")
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
        return h.redirect_back(h.form_reader_id(), "librarian")

    @app.post("/unblock")
    def unblock_reader():
        if not h.require_librarian_mode():
            return h.redirect_back(h.form_reader_id(), "reader")
        target_id = pick_reader_id(
            request.form.get("target_reader_id", ""),
            reader_ids(ctx),
            default_reader_id(ctx),
        )
        return h.run_action(
            lambda: ctx.admin_service.unblock_reader(LIBRARIAN_ID, target_id),
            "Читача розблоковано.",
            h.form_reader_id(),
            "librarian",
        )
