"""Deterministic Budget / Balanced / Comfort plan optimizer (exhaustive over small option sets)."""
from __future__ import annotations
from dataclasses import dataclass
from itertools import product

PROFILES = {  # weights on normalised cost, travel time, discomfort
    "budget":   {"cost": 0.70, "time": 0.15, "comfort": 0.15},
    "balanced": {"cost": 0.40, "time": 0.25, "comfort": 0.35},
    "comfort":  {"cost": 0.15, "time": 0.25, "comfort": 0.60},
}


@dataclass(frozen=True)
class Option:
    id: str
    cost: float
    comfort: float            # 0..1, higher is better
    travel_hours: float = 0.0


def _norm(v, lo, hi):
    return 0.0 if hi == lo else (v - lo) / (hi - lo)


def optimize(flights, hotels, budget: float | None = None) -> dict:
    if not flights or not hotels:
        raise ValueError("need at least one flight and one hotel option")
    combos = list(product(flights, hotels))
    cost = [f.cost + h.cost for f, h in combos]
    time = [f.travel_hours + h.travel_hours for f, h in combos]
    comf = [(f.comfort + h.comfort) / 2 for f, h in combos]
    out = {}
    for name, w in PROFILES.items():
        best = None
        for i, (f, h) in enumerate(combos):
            if budget is not None and cost[i] > budget and name != "comfort":
                continue
            s = (w["cost"] * _norm(cost[i], min(cost), max(cost))
                 + w["time"] * _norm(time[i], min(time), max(time))
                 + w["comfort"] * (1 - _norm(comf[i], min(comf), max(comf))))
            key = (s, cost[i], f.id, h.id)
            if best is None or key < best[0]:
                best = (key, f, h, cost[i], comf[i])
        out[name] = None if best is None else {
            "flight": best[1].id, "hotel": best[2].id, "cost": round(best[3], 2),
            "comfort": round(best[4], 3), "score": round(best[0][0], 4),
            "within_budget": budget is None or best[3] <= budget}
    return out
