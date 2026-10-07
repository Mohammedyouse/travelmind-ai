from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ItineraryItem:
    day: int
    title: str
    description: str | None = None
    cost: float = 0.0


@dataclass
class BudgetEstimate:
    currency: str = "USD"
    subtotal: float = 0.0
    contingency: float = 0.0
    total: float = 0.0
    remaining: float | None = None
    over_budget: bool = False


@dataclass
class TripCreateRequest:
    origin: str
    destination: str
    departure_date: str | None = None
    return_date: str | None = None
    duration_days: int | None = None
    travelers: int = 1
    budget: float | None = None
    currency: str = "USD"
    interests: list[str] = field(default_factory=list)
    preferences: dict[str, Any] = field(default_factory=dict)


@dataclass
class TripReadModel:
    trip_id: str
    destination: str
    status: str = "draft"
    itinerary: list[ItineraryItem] = field(default_factory=list)
    budget: BudgetEstimate | None = None
