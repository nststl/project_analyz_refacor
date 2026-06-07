from __future__ import annotations

from datetime import timedelta

from flask import Flask, flash, redirect, render_template, request

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
from web.route_helpers import RouteHelpers
from web.security import (
    clamp_advance_days,
    clamp_block_days,
    pick_book_id,
    pick_mode,
    pick_penalty_kind,
    pick_reader_id,
    safe_error_message,
    sanitize_search_query,
)
from web.simulation import advance_simulation_days, apply_penalty_strategy, log_event, parse_penalty_rate


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

        def _borrow() -> None:
            loan = ctx.loan_service.borrow(rid, bid)
            title = ctx.books.get_by_id(bid)
            log_event(
                ctx,
                f"UC-01 {rid} взяв «{title.title if title else bid}» (до {loan.due_at.date()})",
            )

        return h.run_action(
            _borrow,
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
                log_event(
                    ctx,
                    f"UC-03 Повернення з штрафом {loan.penalty_amount} грн (+{overdue} дн.)",
                )
            else:
                log_event(ctx, "UC-02 Повернення вчасно, штраф 0 грн")
            if ctx.observer.notifications:
                last = ctx.observer.notifications[-1]
                log_event(ctx, f"UC-05 Observer: книга {last[0]} доступна для {last[1]}")

        return h.run_action(_return, "Книгу повернено.", rid, mode)

    @app.post("/reserve")
    def reserve():
        rid, mode = h.form_reader_id(), h.form_mode()
        bid = pick_book_id(request.form.get("book_id", ""), book_ids(ctx))

        def _reserve() -> None:
            ctx.reservation_service.enqueue(rid, bid)
            log_event(ctx, f"UC-04 Резерв: {rid} → {bid}")

        return h.run_action(_reserve, "Додано до черги резерву.", rid, mode)

    @app.post("/cancel-reservation")
    def cancel_reservation():
        rid, mode = h.form_reader_id(), h.form_mode()
        res_id = request.form.get("reservation_id", "")

        def _cancel() -> None:
            ctx.reservation_service.cancel(rid, res_id)
            log_event(ctx, f"Скасовано резерв {res_id}")

        return h.run_action(_cancel, "Резерв скасовано.", rid, mode)

    @app.post("/advance-time")
    def advance_time():
        rid, mode = h.form_reader_id(), h.form_mode()
        days = clamp_advance_days(request.form.get("days", "1"))
        try:
            blocked = advance_simulation_days(ctx, days)
            if blocked:
                flash(
                    f"Час +{days} дн. Автоблокування (UC-07): {len(blocked)} читач(ів).",
                    "success",
                )
            else:
                flash(f"Час симуляції переведено вперед на {days} дн.", "success")
        except (ValueError, RuntimeError):
            flash("Помилка операції.", "error")
        return h.redirect_back(rid, mode)

    @app.post("/set-penalty-strategy")
    def set_penalty_strategy_route():
        rid, mode = h.form_reader_id(), h.form_mode()
        kind = pick_penalty_kind(request.form.get("strategy", "linear"))
        rate = parse_penalty_rate(request.form.get("rate", "10"))
        label = apply_penalty_strategy(ctx, kind, rate)
        flash(f"Стратегія штрафів: {label}", "success")
        return h.redirect_back(rid, mode)

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
            log_event(ctx, f"UC-06 Блокування {target_id} на {days} дн.")
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

        def _unblock() -> None:
            ctx.admin_service.unblock_reader(LIBRARIAN_ID, target_id)
            log_event(ctx, f"UC-06 Розблокування {target_id}")

        return h.run_action(
            _unblock,
            "Читача розблоковано.",
            h.form_reader_id(),
            "librarian",
        )
