from __future__ import annotations

import os
from typing import Any

from ..core.types import TripSpec
from ..integrations.hotels import build_hotel_provider
from .base import TravelAgent


class AccommodationIntelligenceAgent(TravelAgent):
    name = "accommodation_intelligence"
    description = "Researches real accommodations, evaluates rates, and recommends stays matching budget."
    requires = ("trip_spec",)

    def run(self, context: dict[str, Any]):
        trip_spec = context.get("trip_spec") or context.get("state", {}).get("trip_spec")
        if trip_spec is None:
            return self._build_output(
                status="needs_input",
                summary="No trip details available for accommodation planning.",
                missing_fields=["trip_spec"],
            )

        if not isinstance(trip_spec, TripSpec):
            trip_spec = TripSpec.from_dict(trip_spec)

        if trip_spec.budget is None:
            return self._build_output(
                status="needs_input",
                summary="Accommodation planning needs a trip budget.",
                missing_fields=["budget"],
            )

        stay_days = trip_spec.duration_days or 3
        if trip_spec.departure_date and trip_spec.return_date:
            stay_days = max(1, (trip_spec.return_date - trip_spec.departure_date).days)

        nightly_budget = (trip_spec.budget or 0) * 0.35 / max(stay_days, 1)

        hotel_provider = build_hotel_provider()
        check_in = trip_spec.departure_date.isoformat() if trip_spec.departure_date else None
        check_out = trip_spec.return_date.isoformat() if trip_spec.return_date else None

        result = hotel_provider.search_hotels(
            destination=trip_spec.destination or "Destination",
            check_in=check_in,
            check_out=check_out,
            guests=trip_spec.travelers,
            currency=trip_spec.currency,
            max_results=6,
        )

        hotels = result.data.get("hotels", []) if result.ok and result.data else []
        preferred_stays = [f"{h.get('name', 'Boutique Stay')} ({h.get('tier', 'Hotel')})" for h in hotels] if hotels else [
            "Boutique stay near city center",
            "Budget-friendly hostel or social stay",
            "Luxury heritage palace or resort",
        ]

        accommodation_plan = {
            "stay_days": stay_days,
            "target_nightly_budget": round(nightly_budget, 2),
            "preferred_stays": preferred_stays,
            "sensitivity": "cost-aware" if (trip_spec.budget or 0) < 2000 else "balanced",
            "available_hotels": hotels,
            "source": result.data.get("source", "verified_destination_hotels") if result.ok else "unconfigured",
        }

        return self._build_output(
            status="ok",
            summary=f"Suggested accommodation strategy and curated {len(hotels)} verified property option(s) spanning budget hostels to luxury heritage stays for {stay_days} night(s).",
            data={"accommodation": accommodation_plan, "hotels": hotels},
            recommendations=[
                "Explore budget hostels for social community and significant cost savings.",
                "Choose mid-range boutique havelis or historic stays for authentic local culture.",
                "Consider 5-star heritage palaces for milestone celebratory evenings.",
            ],
        )
