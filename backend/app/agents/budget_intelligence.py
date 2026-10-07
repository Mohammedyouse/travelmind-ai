from __future__ import annotations

from typing import Any

from ..core.types import TripSpec
from ..services.budget import compute_budget
from .base import TravelAgent


def _extract_data(agent_output: Any) -> dict[str, Any]:
    if agent_output is None:
        return {}
    if hasattr(agent_output, "data") and isinstance(agent_output.data, dict):
        return agent_output.data
    if isinstance(agent_output, dict):
        return agent_output.get("data", agent_output)
    return {}


class BudgetIntelligenceAgent(TravelAgent):
    name = "budget_intelligence"
    description = "Builds a realistic travel budget and evaluates overrun risks."
    requires = ("trip_spec",)

    def run(self, context: dict[str, Any]):
        trip_spec = context.get("trip_spec") or context.get("state", {}).get("trip_spec")
        if trip_spec is None:
            return self._build_output(
                status="needs_input",
                summary="No trip details available for budget planning.",
                missing_fields=["trip_spec"],
            )

        if not isinstance(trip_spec, TripSpec):
            trip_spec = TripSpec.from_dict(trip_spec)

        if trip_spec.budget is None:
            return self._build_output(
                status="needs_input",
                summary="Budget planning needs a total travel budget.",
                missing_fields=["budget"],
            )

        results = context.get("results", {})
        flight_data = _extract_data(results.get("flight_intelligence"))
        hotel_data = _extract_data(results.get("accommodation_intelligence"))

        flight_offers = flight_data.get("offers", [])
        hotels = hotel_data.get("hotels", [])

        stay_days = trip_spec.duration_days or 4
        if trip_spec.departure_date and trip_spec.return_date:
            stay_days = max(1, (trip_spec.return_date - trip_spec.departure_date).days)

        # Use actual researched prices where available, else realistic budget-derived bounds
        if flight_offers and isinstance(flight_offers, list) and "price" in flight_offers[0]:
            flight_cost = float(flight_offers[0]["price"])
            flight_source = flight_offers[0].get("source", "amadeus-live-search")
        else:
            flight_cost = max(350.0, float(trip_spec.budget) * 0.30)
            flight_source = "development_estimate"

        if hotels and isinstance(hotels, list) and "price_per_night" in hotels[0]:
            hotel_cost = float(hotels[0]["price_per_night"]) * stay_days
            hotel_source = hotels[0].get("source", "verified_destination_hotels")
        else:
            hotel_cost = max(250.0, float(trip_spec.budget) * 0.35)
            hotel_source = "development_estimate"

        is_inr = (trip_spec.currency or "").upper() == "INR"

        if is_inr:
            food_cost = max(800.0 * max(trip_spec.travelers, 1) * stay_days, float(trip_spec.budget) * 0.15)
            transport_cost = max(500.0 * stay_days, float(trip_spec.budget) * 0.10)
            activities_cost = max(600.0 * max(trip_spec.travelers, 1), float(trip_spec.budget) * 0.10)
        else:
            food_cost = max(120.0, float(trip_spec.budget) * 0.15)
            transport_cost = max(80.0, float(trip_spec.budget) * 0.10)
            activities_cost = max(60.0, float(trip_spec.budget) * 0.10)

        estimated_items = {
            "flights": round(flight_cost, 2),
            "accommodation": round(hotel_cost, 2),
            "food": round(food_cost, 2),
            "transport": round(transport_cost, 2),
            "activities": round(activities_cost, 2),
        }

        result = compute_budget(
            estimated_items,
            travelers=trip_spec.travelers,
            contingency_pct=12,
            budget=trip_spec.budget,
            currency=trip_spec.currency,
        )

        sources = {
            "flights": flight_source,
            "accommodation": hotel_source,
            "food": "development_estimate",
            "transport": "development_estimate",
            "activities": "development_estimate",
        }

        return self._build_output(
            status="ok",
            summary=f"Travel budget was evaluated at a total estimate of {result.total} {trip_spec.currency}.",
            data={
                "subtotal": str(result.subtotal),
                "contingency": str(result.contingency),
                "total": str(result.total),
                "remaining": str(result.remaining),
                "over_budget": result.over_budget,
                "currency": result.currency,
                "items": {category: str(amount) for category, amount in result.items.items()},
                "per_person": str(result.per_person),
                "sources": sources,
                "source": "development_estimate",
            },
            recommendations=[
                "Reduce the accommodation category first if costs exceed the traveler’s comfort ceiling.",
                "Keep a contingency buffer for flights and local transport.",
            ],
        )
