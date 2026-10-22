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
        is_usd = curr == "USD"

        # Check if route is domestic India
        orig_upper = (trip_spec.origin or "").upper()
        dest_upper = (trip_spec.destination or "").upper()
        indian_locations = {
            "DEL", "DELHI", "NEW DELHI", "BOM", "MUMBAI", "BLR", "BANGALORE", "BENGALURU",
            "GOA", "GOI", "GOX", "JAI", "JAIPUR", "KERALA", "COK", "KOCHI", "COCHIN",
            "MAA", "CHENNAI", "CCU", "KOLKATA", "HYD", "HYDERABAD", "UDR", "UDAIPUR",
            "VNS", "VARANASI", "KUU", "MANALI", "AGR", "AGRA", "AMD", "AHMEDABAD", "LKO", "LUCKNOW",
        }
        is_domestic_india = any(c in orig_upper for c in indian_locations) and any(c in dest_upper for c in indian_locations)

        # Exchange rate resolution
        fx_rate = 1.0
        if is_inr:
            fx_rate = 84.0
        elif not is_usd:
            try:
                from ..integrations.currency import build_currency_provider
                rates_res = build_currency_provider().get_rates("USD")
                rates = rates_res.data.get("rates", {}) if rates_res.ok and rates_res.data else {}
                fx_rate = float(rates.get(curr, 1.0))
            except Exception:
                fx_rate = 1.0

        # Baseline cost rates scaled to target currency
        if is_domestic_india:
            if is_inr:
                baseline_flight = 5500.0
                nightly_benchmark = 3200.0
                daily_food_pp = 1200.0
                daily_transit_pp = 500.0
                airport_transfers = 1200.0
                daily_activity_pp = 600.0
            else:
                baseline_flight = round(5500.0 / 84.0 * fx_rate, 2)
                nightly_benchmark = round(3200.0 / 84.0 * fx_rate, 2)
                daily_food_pp = round(1200.0 / 84.0 * fx_rate, 2)
                daily_transit_pp = round(500.0 / 84.0 * fx_rate, 2)
                airport_transfers = round(1200.0 / 84.0 * fx_rate, 2)
                daily_activity_pp = round(600.0 / 84.0 * fx_rate, 2)
        else:
            if is_inr:
                baseline_flight = 46200.0
                nightly_benchmark = 7140.0
                daily_food_pp = 3360.0
                daily_transit_pp = 1680.0
                airport_transfers = 4200.0
                daily_activity_pp = 2940.0
            else:
                baseline_flight = round(550.0 * fx_rate, 2)
                nightly_benchmark = round(85.0 * fx_rate, 2)
                daily_food_pp = round(40.0 * fx_rate, 2)
                daily_transit_pp = round(20.0 * fx_rate, 2)
                airport_transfers = round(50.0 * fx_rate, 2)
                daily_activity_pp = round(35.0 * fx_rate, 2)

        # 1. Flight quote vs transparent route corridor estimate
        if flight_offers and isinstance(flight_offers, list) and "price" in flight_offers[0]:
            flight_cost = float(flight_offers[0]["price"])
            flight_source = flight_offers[0].get("source", "amadeus-live-search")
            flight_is_live = True
            flight_notes = f"Live offer quote: {flight_offers[0].get('carrier_names', ['Carrier'])[0]} ({flight_offers[0].get('flight_number', 'Flight')})"
        else:
            flight_cost = round(baseline_flight * travelers, 2)
            flight_source = "unconfigured_provider_estimate"
            flight_is_live = False
            flight_notes = f"Corridor estimate ({curr} {baseline_flight}/traveler round-trip; Amadeus live search unconfigured)"

        # 2. Hotel quote vs benchmark stay estimate
        if hotels and isinstance(hotels, list) and "price_per_night" in hotels[0]:
            h0 = hotels[0]
            nightly = float(h0.get("price_per_night", nightly_benchmark))
            hotel_base = round(nightly * stay_days * rooms, 2)
            taxes_fees = round(hotel_base * 0.12, 2)
            hotel_cost = round(hotel_base + taxes_fees, 2)
            hotel_source = h0.get("source", "verified_destination_hotels")
            hotel_is_live = h0.get("is_live", False)
            hotel_notes = f"{h0.get('name', 'Hotel')} ({stay_days} nights × {rooms} room(s) @ {curr} {nightly}/night + {curr} {taxes_fees} taxes)"
        else:
            taxes_benchmark = round(nightly_benchmark * stay_days * rooms * 0.12, 2)
            hotel_cost = round(nightly_benchmark * stay_days * rooms + taxes_benchmark, 2)
            hotel_source = "estimated_benchmark"
            hotel_is_live = False
            hotel_notes = f"Benchmark estimate ({stay_days} nights × {rooms} room(s) @ {curr} {nightly_benchmark}/night + 12% taxes)"

        # 3. Transparent Food Per-Person/Per-Day Model
        food_cost = round(daily_food_pp * travelers * stay_days, 2)
        food_notes = f"{curr} {daily_food_pp}/traveler/day (breakfast, lunch, dinner, cafe) × {travelers} travelers × {stay_days} days"

        # 4. Transparent Local Transport Model
        transport_cost = round(daily_transit_pp * travelers * stay_days + airport_transfers, 2)
        transport_notes = f"Airport transfers ({curr} {airport_transfers}) + metro/rideshare ({curr} {daily_transit_pp}/day/traveler)"

        # 5. Activities & Sightseeing Model
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
