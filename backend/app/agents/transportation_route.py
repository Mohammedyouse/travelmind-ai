from __future__ import annotations

from typing import Any

from ..core.types import TripSpec
from ..integrations.base import resolve_iata
from .base import TravelAgent


class TransportationRouteAgent(TravelAgent):
    name = "transportation_route"
    description = "Designs local travel routing, airport transfers, and transit recommendations."
    requires = ("trip_spec",)

    def run(self, context: dict[str, Any]):
        trip_spec = context.get("trip_spec") or context.get("state", {}).get("trip_spec")
        if trip_spec is None:
            return self._build_output(
                status="needs_input",
                summary="No trip context available for route planning.",
                missing_fields=["trip_spec"],
            )

        if not isinstance(trip_spec, TripSpec):
            trip_spec = TripSpec.from_dict(trip_spec)

        if not trip_spec.origin or not trip_spec.destination:
            return self._build_output(
                status="needs_input",
                summary="Origin and destination are required for route planning.",
                missing_fields=["origin", "destination"],
            )

        origin_code = resolve_iata(trip_spec.origin)
        dest_code = resolve_iata(trip_spec.destination)

        route_plan = {
            "route": f"{trip_spec.origin} -> {trip_spec.destination}",
            "origin_iata": origin_code,
            "destination_iata": dest_code,
            "transport_modes": ["airport transfer", "rideshare", "public transit", "walking tour"],
            "transit_options": [
                {"mode": "Airport Express Train / Metro", "estimated_cost_usd": 12.0, "time_mins": 35, "recommendation": "Best value for arrival transfer"},
                {"mode": "Rideshare / Licensed Taxi", "estimated_cost_usd": 32.0, "time_mins": 25, "recommendation": "Convenient with heavy luggage"},
                {"mode": "City Multi-Day Transit Pass", "estimated_cost_usd": 22.0, "time_mins": 0, "recommendation": "Unlimited metro, tram, and buses"},
            ],
            "recommendation": "Use a hybrid strategy: airport transfer + public transit + walking for city exploration.",
            "travel_style": "efficient_and_cost_sensitive",
        }

        return self._build_output(
            status="ok",
            summary=f"Transit and route recommendations prepared for {trip_spec.origin} to {trip_spec.destination}.",
            data={"route": route_plan},
            recommendations=[
                "Purchase an unlimited city transit pass on arrival to save up to 40% on urban travel.",
                "Minimize backtracking by clustering nearby sights during morning and afternoon outings.",
            ],
        )
