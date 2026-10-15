from __future__ import annotations

from datetime import datetime
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
        dep_str = trip_spec.departure_date.isoformat() if trip_spec.departure_date else None
        ret_str = trip_spec.return_date.isoformat() if trip_spec.return_date else None
        weather_res = weather_provider.get_forecast(lat, lon, days=min(stay_days, 14), departure_date=dep_str, return_date=ret_str)

        weather_notes = []
        forecast = []
        is_beyond_horizon = False
        horizon_notice = None
        current_weather = None

        if weather_res.ok and weather_res.data:
            wdata = weather_res.data
            is_beyond_horizon = wdata.get("is_beyond_horizon", False)
            horizon_notice = wdata.get("horizon_notice")
            current_weather = wdata.get("current")
            forecast = wdata.get("forecast", [])

            if is_beyond_horizon:
                weather_notes.append(f"Destination Current Conditions ({dest}): {current_weather.get('condition', 'Clear')}, {current_weather.get('temperature_c', 'N/A')}°C.")
                if horizon_notice:
                    weather_notes.append(f"Notice: {horizon_notice}")
                weather_notes.append("Pack baseline climate attire and verify forecast 10 days before departure.")
            elif forecast:
                first_day = forecast[0]
                temp_max = first_day.get("temp_max_c")
                cond = first_day.get("condition")
                rain_prob = max((d.get("precipitation_probability_pct", 0) for d in forecast), default=0)
                highest_temp = max((d.get("temp_max_c", 20) for d in forecast if d.get("temp_max_c") is not None), default=20)
                lowest_temp = min((d.get("temp_min_c", 15) for d in forecast if d.get("temp_min_c") is not None), default=15)

                weather_notes.append(f"Live Open-Meteo Forecast for {dest}: {cond}, highs around {temp_max}°C (Trip range: {lowest_temp}°C to {highest_temp}°C).")
                if rain_prob > 30:
                    weather_notes.append(f"Rain probability reaches {rain_prob}%: Pack a compact windproof umbrella and waterproof footwear.")
                if highest_temp > 28:
                    weather_notes.append("Warm temperatures expected: Pack SPF 50 sunscreen, UV sunglasses, and breathable cotton/linen.")
                elif lowest_temp < 14:
                    weather_notes.append("Cool mornings/evenings expected: Pack a lightweight fleece, thermal layers, and a warm evening jacket.")

        checklist = [
            "Confirm passport validity (at least 6 months remaining) and check visa entry rules.",
            "Set up international travel health insurance and offline itinerary access.",
            "Pack universal travel power adapters and portable USB battery bank.",
        ] + weather_notes

        support = {
            "destination": dest,
            "checklist": checklist,
            "weather_forecast": forecast[:7] if forecast else (weather_res.data.get("upcoming_reference_forecast", [])[:5] if is_beyond_horizon else []),
            "current_weather": current_weather,
            "is_beyond_horizon": is_beyond_horizon,
            "horizon_notice": horizon_notice,
            "weather_retrieved_at": weather_res.data.get("retrieved_at") if weather_res.ok and weather_res.data else None,
            "weather_source": "open-meteo.com",
            "notifications": [
                "Flight reminder (48h before departure)",
                "Hotel check-in instructions (24h before arrival)",
                "Daily itinerary morning briefing",
                "Budget guardrail alert",
            ],
            "emergency_numbers": {
                "police_ambulance": "112 (Europe/India) / 911 (US/Americas) / 110 (Japan)",
                "embassy_assistance": f"Contact national diplomatic mission in {dest}",
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
