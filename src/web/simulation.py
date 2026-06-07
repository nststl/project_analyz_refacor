from __future__ import annotations

from decimal import Decimal, InvalidOperation

from patterns.penalty_strategy import LinearPenaltyStrategy, TieredPenaltyStrategy
from utils.time_utils import calendar_overdue_days
from web.context import LibraryContext

_DEFAULT_PENALTY_RATE = Decimal("10")
_MAX_EVENT_LOG = 80


def log_event(ctx: LibraryContext, message: str) -> None:
    ts = ctx.clock.now().strftime("%Y-%m-%d %H:%M")
    ctx.event_log.append(f"[{ts}] {message}")
    if len(ctx.event_log) > _MAX_EVENT_LOG:
        ctx.event_log[:] = ctx.event_log[-_MAX_EVENT_LOG:]


def advance_simulation_days(ctx: LibraryContext, days: int) -> list[str]:
    before = ctx.clock.now()
    ctx.clock.advance_days(days)
    after = ctx.clock.now()
    log_event(ctx, f"Час переведено вперед на {days} дн. ({before.date()} → {after.date()})")

    blocked = ctx.auto_blocking.enforce_overdue_active_loans(
        ctx.loans, ctx.books, ctx.loan_service.penalty_strategy, after
    )
    messages: list[str] = []
    for user in blocked:
        log_event(
            ctx,
            f"UC-07 Автоблокування: {user.name} ({user.id}) — прострочені позики",
        )
        messages.append(user.id)
    return messages


def apply_penalty_strategy(ctx: LibraryContext, kind: str, rate: Decimal) -> str:
    if kind == "tiered":
        strategy = TieredPenaltyStrategy(rate, rate * 2, threshold_days=7)
        label = f"Tiered ({rate}/{rate * 2} грн/день після 7 дн.)"
    else:
        strategy = LinearPenaltyStrategy(rate)
        label = f"Linear ({rate} грн/день, RARE ×2)"
    ctx.loan_service.set_penalty_strategy(strategy)
    ctx.penalty_kind = kind
    ctx.penalty_rate = rate
    log_event(ctx, f"Стратегія штрафів: {label}")
    return label


def parse_penalty_rate(raw: str | None, *, default: Decimal = _DEFAULT_PENALTY_RATE) -> Decimal:
    if raw is None or not str(raw).strip():
        return default
    try:
        value = Decimal(str(raw).strip())
    except InvalidOperation:
        return default
    if value <= 0 or value > Decimal("1000"):
        return default
    return value


def reader_estimated_penalty(ctx: LibraryContext, user_id: str) -> Decimal:
    total = Decimal("0")
    for loan in ctx.loan_service.active_loans_for(user_id):
        total += ctx.loan_service.estimated_penalty(loan)
    return total


def build_loan_row(ctx: LibraryContext, loan) -> dict:
    now = ctx.clock.now()
    overdue = calendar_overdue_days(loan.due_at, now)
    estimated = ctx.loan_service.estimated_penalty(loan, now)
    days_left = (loan.due_at.date() - now.date()).days
    if overdue > 0:
        status = "overdue"
        status_label = f"ПРОСТРОЧЕНО +{overdue} ДН."
    elif days_left == 0:
        status = "due_today"
        status_label = "ДЕДЛАЙН СЬОГОДНІ"
    else:
        status = "active"
        status_label = f"АКТИВНА (ЩЕ {days_left} ДН.)"
    return {
        "loan": loan,
        "overdue_days": overdue,
        "estimated_penalty": estimated,
        "status": status,
        "status_label": status_label,
    }
