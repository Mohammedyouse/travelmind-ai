"""Deterministic budget engine. No LLM arithmetic: all money math is Decimal-based.

Exchange rates are NEVER hardcoded here; callers must supply rates fetched from a
currency provider (or an explicit user-supplied table in dev mode).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Mapping

CENT = Decimal("0.01")


class BudgetError(ValueError):
    pass


def D(x) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


def money(x) -> Decimal:
    return D(x).quantize(CENT, rounding=ROUND_HALF_UP)


def convert(amount, src: str, dst: str, rates_to_usd: Mapping[str, object]) -> Decimal:
    """Convert via a USD pivot. rates_to_usd[c] = units of c per 1 USD."""
    if src == dst:
        return money(amount)
    for c in (src, dst):
        if c != "USD" and c not in rates_to_usd:
            raise BudgetError(f"missing exchange rate for {c}")
    r = lambda c: Decimal(1) if c == "USD" else D(rates_to_usd[c])
    if r(src) <= 0 or r(dst) <= 0:
        raise BudgetError("exchange rates must be positive")
    return money(D(amount) / r(src) * r(dst))


@dataclass
class BudgetResult:
    currency: str
    items: dict
    subtotal: Decimal
    contingency: Decimal
    total: Decimal
    budget: Decimal | None
    remaining: Decimal | None
    over_budget: bool
    per_person: Decimal
    sources: dict = field(default_factory=dict)  # category -> "live" | "estimate" | "user"


def compute_budget(items: Mapping[str, object], *, travelers: int = 1,
                   contingency_pct: object = "10", budget=None, currency: str = "USD",
                   sources: Mapping[str, str] | None = None) -> BudgetResult:
    if travelers < 1:
        raise BudgetError("travelers must be >= 1")
    pct = D(contingency_pct)
    if pct < 0 or pct > 100:
        raise BudgetError("contingency_pct must be within 0..100")
    clean = {}
    for k, v in items.items():
        v = D(v)
        if v < 0:
            raise BudgetError(f"negative amount for {k}")
        clean[k] = money(v)
    subtotal = money(sum(clean.values(), Decimal(0)))
    cont = money(subtotal * pct / 100)
    total = money(subtotal + cont)
    b = money(budget) if budget is not None else None
    return BudgetResult(currency, clean, subtotal, cont, total, b,
                        money(b - total) if b is not None else None,
                        bool(b is not None and total > b),
                        money(total / travelers), dict(sources or {}))


def reduce_category(items: Mapping[str, object], category: str, pct) -> dict:
    """Deterministic 'reduce hotel spending by 20%'."""
    if category not in items:
        raise BudgetError(f"unknown category {category}")
    p = D(pct)
    if not 0 <= p <= 100:
        raise BudgetError("pct must be within 0..100")
    out = {k: money(v) for k, v in items.items()}
    out[category] = money(D(items[category]) * (100 - p) / 100)
    return out


def feasibility(total_budget, days: int, travelers: int, min_daily_pp) -> dict:
    """Flag unrealistic budgets against a caller-supplied minimum daily cost per person."""
    need = money(D(min_daily_pp) * days * travelers)
    b = money(total_budget)
    return {"realistic": b >= need, "minimum_needed": need, "shortfall": money(max(need - b, Decimal(0)))}
