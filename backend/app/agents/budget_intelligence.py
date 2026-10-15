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
        dest_data = _extract_data(results.get("destination_discovery"))

        flight_offers = flight_data.get("offers", [])
        hotels = hotel_data.get("hotels", [])

        stay_days = trip_spec.duration_days or 4
        if trip_spec.departure_date and trip_spec.return_date:
            stay_days = max(1, (trip_spec.return_date - trip_spec.departure_date).days)

        travelers = max(trip_spec.travelers or 1, 1)
        rooms = max(1, (travelers + 1) // 2)
        curr = (trip_spec.currency or "USD").upper()
        is_inr = curr == "INR"

        # 1. Flight quote vs transparent route corridor estimate
        if flight_offers and isinstance(flight_offers, list) and "price" in flight_offers[0]:
            flight_cost = float(flight_offers[0]["price"])
            flight_source = flight_offers[0].get("source", "amadeus-live-search")
            flight_is_live = True
            flight_notes = f"Live offer quote: {flight_offers[0].get('carrier_names', ['Carrier'])[0]} ({flight_offers[0].get('flight_number', 'Flight')})"
        else:
            # Baseline route allowance per traveler round-trip
            baseline_per_traveler = 5500.0 if is_inr else 550.0
            flight_cost = round(baseline_per_traveler * travelers, 2)
            flight_source = "unconfigured_provider_estimate"
            flight_is_live = False
            flight_notes = f"Corridor estimate ({curr} {baseline_per_traveler}/traveler round-trip; Amadeus live search unconfigured)"

        # 2. Hotel quote vs benchmark stay estimate
        if hotels and isinstance(hotels, list) and "price_per_night" in hotels[0]:
            h0 = hotels[0]
            nightly = float(h0.get("price_per_night", 100.0))
            taxes_fees = float(h0.get("taxes_and_fees", nightly * stay_days * rooms * 0.12))
            hotel_cost = float(h0.get("total_stay_price", nightly * stay_days * rooms + taxes_fees))
            hotel_source = h0.get("source", "verified_destination_hotels")
            hotel_is_live = h0.get("is_live", False)
            hotel_notes = f"{h0.get('name', 'Hotel')} ({stay_days} nights × {rooms} room(s) @ {curr} {nightly}/night + {curr} {taxes_fees} taxes)"
        else:
            nightly_benchmark = 3200.0 if is_inr else 85.0
            taxes_benchmark = round(nightly_benchmark * stay_days * rooms * 0.12, 2)
            hotel_cost = round(nightly_benchmark * stay_days * rooms + taxes_benchmark, 2)
            hotel_source = "estimated_benchmark"
            hotel_is_live = False
            hotel_notes = f"Benchmark estimate ({stay_days} nights × {rooms} room(s) @ {curr} {nightly_benchmark}/night + 12% taxes)"

        # 3. Transparent Food Per-Person/Per-Day Model
        daily_food_pp = 1200.0 if is_inr else 40.0
        food_cost = round(daily_food_pp * travelers * stay_days, 2)
        food_notes = f"{curr} {daily_food_pp}/traveler/day (breakfast, lunch, dinner, cafe) × {travelers} travelers × {stay_days} days"

        # 4. Transparent Local Transport Model
        daily_transit_pp = 500.0 if is_inr else 20.0
        airport_transfers = 1200.0 if is_inr else 50.0
        transport_cost = round(daily_transit_pp * travelers * stay_days + airport_transfers, 2)
        transport_notes = f"Airport transfers ({curr} {airport_transfers}) + metro/rideshare ({curr} {daily_transit_pp}/day/traveler)"

        # 5. Activities & Sightseeing Model
        daily_activity_pp = 600.0 if is_inr else 35.0
        activity_days = min(stay_days, 5)
        activities_cost = round(daily_activity_pp * travelers * activity_days, 2)
        activities_notes = f"Monument entry fees & cultural activities ({curr} {daily_activity_pp}/day/traveler × {activity_days} active days)"

        estimated_items = {
            "flights": round(flight_cost, 2),
            "accommodation": round(hotel_cost, 2),
            "food": round(food_cost, 2),
            "transport": round(transport_cost, 2),
            "activities": round(activities_cost, 2),
        }

        result = compute_budget(
            estimated_items,
            travelers=travelers,
            contingency_pct=12,
            budget=trip_spec.budget,
            currency=curr,
        )

        sources = {
            "flights": flight_source,
            "accommodation": hotel_source,
            "food": "transparent_daily_allowance_model",
            "transport": "transparent_transit_model",
            "activities": "sightseeing_entry_model",
        }

        item_explanations = {
            "flights": flight_notes,
            "accommodation": hotel_notes,
            "food": food_notes,
            "transport": transport_notes,
            "activities": activities_notes,
        }

        # Accurate completeness and over-budget determination
        has_live_quotes = flight_is_live and hotel_is_live
        budget_status = "OVER_BUDGET" if result.over_budget else ("WITHIN_BUDGET_VERIFIED" if has_live_quotes else "WITHIN_BUDGET_ESTIMATED")
        status_message = (
            f"Caution: Total estimated cost ({result.total} {curr}) exceeds the budget ceiling ({trip_spec.budget} {curr})."
            if result.over_budget else
            (f"Itinerary is mathematically within budget ({result.remaining} {curr} remaining buffer)."
             if has_live_quotes else
             f"Itinerary is within estimated bounds ({result.remaining} {curr} remaining). Live flight/hotel quotes unconfigured.")
        )

        return self._build_output(
            status="ok",
            summary=f"Trip budget synthesized: subtotal {result.subtotal} {curr} + 12% contingency buffer ({result.contingency} {curr}) = {result.total} {curr}. Status: {budget_status}.",
            data={
                "subtotal": str(result.subtotal),
                "contingency": str(result.contingency),
                "total": str(result.total),
                "remaining": str(result.remaining),
                "over_budget": result.over_budget,
                "budget_status": budget_status,
                "status_message": status_message,
                "currency": result.currency,
                "items": {category: str(amount) for category, amount in result.items.items()},
                "item_explanations": item_explanations,
                "per_person": str(result.per_person),
                "sources": sources,
                "stay_days": stay_days,
                "travelers": travelers,
                "rooms": rooms,
                "has_live_quotes": has_live_quotes,
                "source": "development_estimate",
            },
            recommendations=[
                "Review itemized breakdown before confirming bookings.",
                "Reserve early if traveling during peak season to preserve contingency buffer.",
            ],
        )
