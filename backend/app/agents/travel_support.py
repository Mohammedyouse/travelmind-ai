from __future__ import annotations

from typing import Any

from ..core.types import TripSpec
from ..integrations.places import build_places_provider
from ..integrations.weather import build_weather_provider
from .base import TravelAgent


class TravelSupportAgent(TravelAgent):
    name = "travel_support"
    description = "Prepares traveler support items, weather-tailored packing advice, reminders, and proactive assistance."
    requires = ("trip_spec",)

    def run(self, context: dict[str, Any]):
        trip_spec = context.get("trip_spec") or context.get("state", {}).get("trip_spec")
        if trip_spec is None:
            return self._build_output(
                status="needs_input",
                summary="No trip context available for support planning.",
                missing_fields=["trip_spec"],
            )

        if not isinstance(trip_spec, TripSpec):
            trip_spec = TripSpec.from_dict(trip_spec)

        dest = trip_spec.destination or "Destination"
        places_provider = build_places_provider()
        coords = places_provider.geocode(dest)
        lat, lon = coords if coords else (48.8566, 2.3522)

        weather_provider = build_weather_provider()
        stay_days = trip_spec.duration_days or 4
        weather_res = weather_provider.get_forecast(lat, lon, days=min(stay_days, 7))

        weather_notes = []
        forecast = []
        if weather_res.ok and weather_res.data:
            forecast = weather_res.data.get("forecast", [])
            if forecast:
                first_day = forecast[0]
                temp_max = first_day.get("temp_max_c")
                cond = first_day.get("condition")
                rain_prob = first_day.get("precipitation_probability_pct", 0)
                weather_notes.append(f"Expected arrival weather in {dest}: {cond}, up to {temp_max}°C.")
                if rain_prob > 30:
                    weather_notes.append("Pack a compact travel umbrella or lightweight rain jacket.")
                if temp_max and temp_max > 25:
                    weather_notes.append("Pack sunscreen, sunglasses, and breathable light fabrics.")
                elif temp_max and temp_max < 12:
                    weather_notes.append("Pack thermal layers, warm sweater, and a wind-resistant jacket.")

        checklist = [
            "Confirm passport validity (at least 6 months remaining) and visa requirements.",
            "Set up digital travel insurance and offline itinerary copies.",
            "Review baggage allowance and electronic device power adapters.",
        ] + weather_notes

        support = {
            "destination": dest,
            "checklist": checklist,
            "weather_forecast": forecast[:5],
            "notifications": [
                "Flight reminder (48h before departure)",
                "Hotel check-in instructions (24h before arrival)",
                "Daily itinerary morning briefing",
                "Budget guardrail alert",
            ],
            "emergency_numbers": {
                "police_ambulance": "112 (Europe) / 911 (US/Americas) / 110 (Japan)",
                "embassy_assistance": "Contact national consulate in destination",
            },
        }

        return self._build_output(
            status="ok",
            summary=f"Support workflow and weather-tailored briefing prepared for {dest}.",
            data={"support": support, "weather": weather_res.data if weather_res.ok else None},
            recommendations=[
                "Send flight and accommodation reminders 48 hours before departure.",
                "Trigger itinerary check-ins at each morning checkpoint.",
            ],
        )
