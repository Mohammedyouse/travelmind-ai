"""Weather provider integration.
Supports Open-Meteo REST API (real forecasts, no API key needed) and OpenWeatherMap."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Optional

from ..core.types import ProviderResult
from .base import Transport, urllib_transport

WMO_WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


class WeatherProvider(ABC):
    name: str

    @abstractmethod
    def get_forecast(
        self,
        latitude: float,
        longitude: float,
        days: int = 7,
        departure_date: Optional[str] = None,
        return_date: Optional[str] = None,
    ) -> ProviderResult:
        ...


class UnconfiguredWeatherProvider(WeatherProvider):
    name = "unconfigured_weather"

    def __init__(self, reason: str = "Weather provider not configured"):
        self.reason = reason

    def get_forecast(
        self,
        latitude: float,
        longitude: float,
        days: int = 7,
        departure_date: Optional[str] = None,
        return_date: Optional[str] = None,
    ) -> ProviderResult:
        return ProviderResult(self.name, "unconfigured", None, self.reason)


class OpenMeteoWeatherProvider(WeatherProvider):
    """Open-Meteo provides free, real-time weather forecasts and current conditions without requiring an API key."""
    name = "open_meteo"

    def __init__(self, transport: Transport = urllib_transport, timeout: float = 10.0):
        self.t = transport
        self.timeout = timeout

    def get_forecast(
        self,
        latitude: float,
        longitude: float,
        days: int = 7,
        departure_date: Optional[str] = None,
        return_date: Optional[str] = None,
    ) -> ProviderResult:
        now_utc = datetime.now(timezone.utc)
        today = now_utc.date()

        # Check if trip dates exceed live forecast horizon (14 days)
        is_beyond_horizon = False
        days_ahead = 0
        if departure_date:
            try:
                dep_dt = datetime.fromisoformat(departure_date).date()
                days_ahead = (dep_dt - today).days
                if days_ahead > 14:
                    is_beyond_horizon = True
            except Exception:
                pass

        try:
            params = urllib.parse.urlencode({
                "latitude": f"{latitude:.4f}",
                "longitude": f"{longitude:.4f}",
                "current": "temperature_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
                "daily": "temperature_2m_max,temperature_2m_min,apparent_temperature_max,apparent_temperature_min,weathercode,precipitation_probability_max,wind_speed_10m_max",
                "timezone": "auto",
                "forecast_days": min(max(days, 1), 14),
            })
            url = f"https://api.open-meteo.com/v1/forecast?{params}"
            st, raw = self.t("GET", url, {"User-Agent": "TravelMindAI/1.0"}, None, self.timeout)
            if st != 200:
                return ProviderResult(self.name, "error", None, f"Open-Meteo returned HTTP {st}")

            payload = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)

            # Parse current conditions
            current_raw = payload.get("current", {})
            current_code = current_raw.get("weather_code", 0)
            current_weather = {
                "temperature_c": current_raw.get("temperature_2m"),
                "apparent_temperature_c": current_raw.get("apparent_temperature"),
                "wind_speed_kmh": current_raw.get("wind_speed_10m"),
                "precipitation_mm": current_raw.get("precipitation", 0.0),
                "condition": WMO_WEATHER_CODES.get(current_code, "Clear"),
                "weather_code": current_code,
                "recorded_at": current_raw.get("time"),
            }

            daily = payload.get("daily", {})
            times = daily.get("time", [])
            max_temps = daily.get("temperature_2m_max", [])
            min_temps = daily.get("temperature_2m_min", [])
            app_max_temps = daily.get("apparent_temperature_max", [])
            app_min_temps = daily.get("apparent_temperature_min", [])
            codes = daily.get("weathercode", [])
            rain_probs = daily.get("precipitation_probability_max", [])
            wind_speeds = daily.get("wind_speed_10m_max", [])

            forecast_days = []
            for i in range(len(times)):
                code = codes[i] if i < len(codes) else 0
                forecast_days.append({
                    "date": times[i],
                    "temp_max_c": max_temps[i] if i < len(max_temps) else None,
                    "temp_min_c": min_temps[i] if i < len(min_temps) else None,
                    "apparent_max_c": app_max_temps[i] if i < len(app_max_temps) else None,
                    "apparent_min_c": app_min_temps[i] if i < len(app_min_temps) else None,
                    "condition": WMO_WEATHER_CODES.get(code, "Clear"),
                    "precipitation_probability_pct": rain_probs[i] if i < len(rain_probs) else 0,
                    "wind_speed_max_kmh": wind_speeds[i] if i < len(wind_speeds) else None,
                    "weather_code": code,
                })

            horizon_note = None
            if is_beyond_horizon:
                horizon_note = (
                    f"The requested travel departure ({departure_date}) is {days_ahead} days away, "
                    f"which exceeds Open-Meteo's 14-day live forecast horizon. "
                    f"Displaying current live destination meteorological conditions. "
                    f"A precise day-by-day forecast will unlock 14 days prior to departure."
                )

            data = {
                "latitude": latitude,
                "longitude": longitude,
                "timezone": payload.get("timezone", "UTC"),
                "elevation_m": payload.get("elevation", 0),
                "current": current_weather,
                "forecast": [] if is_beyond_horizon else forecast_days,
                "upcoming_reference_forecast": forecast_days,
                "is_beyond_horizon": is_beyond_horizon,
                "horizon_notice": horizon_note,
                "forecast_horizon_days": 14,
                "source": "open-meteo.com",
                "retrieved_at": now_utc.isoformat(),
            }
            msg = f"Retrieved live Open-Meteo weather ({'beyond horizon' if is_beyond_horizon else f'{len(forecast_days)} day forecast'})"
            return ProviderResult(self.name, "ok", data, msg)
        except Exception as exc:
            return ProviderResult(self.name, "error", None, f"{type(exc).__name__}: {exc}")


def build_weather_provider(env: dict[str, Any] | None = None) -> WeatherProvider:
    return OpenMeteoWeatherProvider()
