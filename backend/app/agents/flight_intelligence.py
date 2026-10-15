from __future__ import annotations

import os
from typing import Any

from ..core.types import TripSpec
from ..integrations.airports import format_flight_endpoint, resolve_airport
from ..integrations.base import build_flight_provider, resolve_iata
from .base import TravelAgent


class FlightIntelligenceAgent(TravelAgent):
    name = "flight_intelligence"
    description = "Evaluates air travel options and searches for suitable flights via Amadeus adapter."
    requires = ("trip_spec",)

    def run(self, context: dict[str, Any]):
        trip_spec = context.get("trip_spec") or context.get("state", {}).get("trip_spec")
        if trip_spec is None:
            return self._build_output(
                status="needs_input",
                summary="No trip details available for flight search.",
                missing_fields=["trip_spec"],
            )

        if not isinstance(trip_spec, TripSpec):
            trip_spec = TripSpec.from_dict(trip_spec)

        missing = [name for name in ("origin", "destination", "departure_date") if not getattr(trip_spec, name, None)]
        if missing:
            return self._build_output(
                status="needs_input",
                summary="Flight search requires destination and departure details.",
                missing_fields=missing,
            )

        merged_env = {
            "AMADEUS_CLIENT_ID": context.get("AMADEUS_CLIENT_ID") or os.getenv("AMADEUS_CLIENT_ID"),
            "AMADEUS_CLIENT_SECRET": context.get("AMADEUS_CLIENT_SECRET") or os.getenv("AMADEUS_CLIENT_SECRET"),
            "AMADEUS_BASE_URL": context.get("AMADEUS_BASE_URL") or os.getenv("AMADEUS_BASE_URL", "https://test.api.amadeus.com"),
        }
        provider = context.get("flight_provider") or build_flight_provider(merged_env)

        depart_str = trip_spec.departure_date.isoformat() if trip_spec.departure_date else ""
        return_str = trip_spec.return_date.isoformat() if trip_spec.return_date else None

        result = provider.search(
            trip_spec.origin or "",
            trip_spec.destination or "",
            depart_str,
            adults=trip_spec.travelers,
            currency=trip_spec.currency,
            max_results=50,
            return_date=return_str,
        )

        origin_code = resolve_iata(trip_spec.origin or "")
        dest_code = resolve_iata(trip_spec.destination or "")
        direct_search_url = f"https://www.google.com/travel/flights?q=flights+from+{origin_code}+to+{dest_code}+on+{depart_str}"
        if return_str:
            direct_search_url += f"+return+{return_str}"

        if result.status == "ok" and result.data:
            offers = result.data
            summary_msg = f"Found {len(offers)} live flight offer(s) for the route {origin_code} -> {dest_code} via Amadeus."
            return self._build_output(
                status="ok",
                summary=summary_msg,
                data={
                    "offers": offers,
                    "total_offers": len(offers),
                    "provider": "amadeus",
                    "provider_status": "live",
                    "direct_search_url": direct_search_url,
                    "origin_iata": origin_code,
                    "destination_iata": dest_code,
                    "origin_airport": resolve_airport(origin_code),
                    "destination_airport": resolve_airport(dest_code),
                },
                recommendations=[
                    "Compare best-value flights by total cost and layover time.",
                    "Review baggage policies and departure terminals before booking.",
                ],
            )

        # Honest unconfigured / error state when credentials are unconfigured or provider returns no data
        is_unconfigured = result.status == "unconfigured" or not merged_env.get("AMADEUS_CLIENT_ID")
        summary_msg = (
            f"Live flight offers are currently unavailable for {origin_code} -> {dest_code}: "
            f"Amadeus Self-Service API credentials are not configured."
            if is_unconfigured else
            f"Amadeus flight search returned no live offers or error: {result.message or 'No routes found'}."
        )

        return self._build_output(
            status="unconfigured" if is_unconfigured else "ok",
            summary=summary_msg,
            data={
                "offers": [],
                "total_offers": 0,
                "provider": "amadeus",
                "provider_status": "unconfigured" if is_unconfigured else result.status,
                "direct_search_url": direct_search_url,
                "missing_credentials": ["AMADEUS_CLIENT_ID", "AMADEUS_CLIENT_SECRET"] if is_unconfigured else [],
                "origin_iata": origin_code,
                "destination_iata": dest_code,
                "origin_airport": resolve_airport(origin_code),
                "destination_airport": resolve_airport(dest_code),
                "message": (
                    "Live pricing and airline offers are currently unavailable because Amadeus credentials "
                    "are not configured in the backend environment. Configure AMADEUS_CLIENT_ID and AMADEUS_CLIENT_SECRET in .env."
                ) if is_unconfigured else f"Provider message: {result.message}",
                "guidance": f"To view live flight schedules, please search directly on airline websites or travel aggregators for {origin_code} -> {dest_code}.",
            },
            recommendations=[
                "Set AMADEUS_CLIENT_ID and AMADEUS_CLIENT_SECRET in backend .env to enable real-time flight search.",
                "Review direct carrier websites for current promotional route pricing.",
            ],
        )
