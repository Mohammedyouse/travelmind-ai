"""Explainable weighted recommender. Every score is decomposed per criterion."""
from __future__ import annotations
from dataclasses import dataclass

DEFAULT_WEIGHTS = {"budget": 0.30, "interests": 0.30, "rating": 0.15,
                   "distance": 0.10, "traveler_fit": 0.10, "season": 0.05}


@dataclass
class Candidate:
    id: str
    price: float                       # total cost for the party, same currency as budget
    tags: frozenset = frozenset()
    rating: float | None = None        # 0..5; None if unsourced
    distance_km: float | None = None
    traveler_types: frozenset = frozenset()
    best_months: frozenset | None = None


@dataclass
class Profile:
    budget: float
    interests: frozenset
    traveler_type: str = "solo"
    month: int | None = None
    max_distance_km: float = 20.0


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def _budget_fit(price: float, budget: float) -> float:
    if budget <= 0:
        return 1.0 if price == 0 else 0.0
    if price <= budget:
        return _clamp(1.0 - 0.3 * price / budget)       # cheaper slightly better; fits => >= 0.7
    return _clamp(0.7 - (price - budget) / budget)       # over budget is penalised steeply


def score(c: Candidate, p: Profile, weights: dict | None = None) -> dict:
    w = dict(weights or DEFAULT_WEIGHTS)
    parts = {
        "budget": _budget_fit(c.price, p.budget),
        "interests": (len(c.tags & p.interests) / len(p.interests)) if p.interests else None,
        "rating": _clamp(c.rating / 5) if c.rating is not None else None,
        "distance": _clamp(1 - c.distance_km / p.max_distance_km) if c.distance_km is not None else None,
        "traveler_fit": ((1.0 if p.traveler_type in c.traveler_types else 0.5) if c.traveler_types else None),
        "season": ((1.0 if p.month in c.best_months else 0.4) if (c.best_months and p.month) else None),
    }
    # Missing criteria are dropped and weights renormalised (never silently scored as zero).
    active = {k: w[k] for k, v in parts.items() if v is not None}
    tot = sum(active.values())
    breakdown = {k: round(parts[k] * active[k] / tot, 4) for k in active}
    return {"id": c.id, "score": round(sum(breakdown.values()), 4), "breakdown": breakdown,
            "missing": sorted(k for k, v in parts.items() if v is None)}


def rank(cands, p: Profile, weights: dict | None = None) -> list:
    return sorted((score(c, p, weights) for c in cands), key=lambda r: (-r["score"], r["id"]))
