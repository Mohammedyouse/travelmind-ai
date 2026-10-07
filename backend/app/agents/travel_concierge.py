from __future__ import annotations

from typing import Any

from ..core.types import TripSpec
from ..integrations.base import resolve_iata
from .base import TravelAgent


class TravelConciergeAgent(TravelAgent):
    name = "travel_concierge"
    description = "Coordinates the entire trip, validates requirements, and enriches traveler context."
    requires = ("trip_spec",)

    def run(self, context: dict[str, Any]):
        trip_spec = context.get("trip_spec") or context.get("state", {}).get("trip_spec")
        if trip_spec is None:
            return self._build_output(
                status="needs_input",
                summary="Trip details have not been provided yet.",
                missing_fields=["trip_spec"],
                recommendations=["Collect origin, destination, dates, travelers, and budget."],
            )

        if not isinstance(trip_spec, TripSpec):
            trip_spec = TripSpec.from_dict(trip_spec)

        missing = trip_spec.missing()
        if missing:
            return self._build_output(
                status="needs_input",
                summary="The trip brief is incomplete; the concierge is waiting for a few details.",
                data={"trip_spec": trip_spec.to_dict(), "missing": missing},
                missing_fields=missing,
                recommendations=[
                    "Ask the traveler for any missing destination, dates, travelers, or budget detail.",
                    "Confirm travel interests so suggestions can be personalized.",
                ],
            )

        duration = trip_spec.duration_days
        if duration is None and trip_spec.departure_date and trip_spec.return_date:
            duration = max(1, (trip_spec.return_date - trip_spec.departure_date).days)

        origin_code = resolve_iata(trip_spec.origin or "")
        dest_code = resolve_iata(trip_spec.destination or "")

        summary = (
            f"The traveler is planning a {duration or 'multi-day'}-day trip from {trip_spec.origin} "
            f"to {trip_spec.destination} with {trip_spec.travelers} traveler(s)."
        )
        return self._build_output(
            status="ok",
            summary=summary,
            data={
                "destination": trip_spec.destination,
                "origin": trip_spec.origin,
                "destination_iata": dest_code,
                "origin_iata": origin_code,
                "duration_days": duration,
                "travelers": trip_spec.travelers,
                "budget": trip_spec.budget,
                "currency": trip_spec.currency,
                "interests": trip_spec.interests,
            },
            recommendations=[
                "Review flights and accommodation options.",
                "Prepare a daily itinerary and local activity recommendations.",
                "Check the trip against the total budget and risk buffer.",
            ],
        )
