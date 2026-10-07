"""Weather provider integration.
Supports Open-Meteo REST API (real forecasts, no API key needed) and OpenWeatherMap."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
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
    def get_forecast(self, latitude: float, longitude: float, days: int = 7) -> ProviderResult:
        ...


class UnconfiguredWeatherProvider(WeatherProvider):
    name = "unconfigured_weather"

    def __init__(self, reason: str = "Weather provider not configured"):
        self.reason = reason

    def get_forecast(self, latitude: float, longitude: float, days: int = 7) -> ProviderResult:
        return ProviderResult(self.name, "unconfigured", None, self.reason)


class OpenMeteoWeatherProvider(WeatherProvider):
    """Open-Meteo provides free, real-time weather forecasts without requiring an API key."""
    name = "open_meteo"

    def __init__(self, transport: Transport = urllib_transport, timeout: float = 10.0):
        self.t = transport
        self.timeout = timeout

    def get_forecast(self, latitude: float, longitude: float, days: int = 7) -> ProviderResult:
        try:
            params = urllib.parse.urlencode({
                "latitude": f"{latitude:.4f}",
                "longitude": f"{longitude:.4f}",
                "daily": "temperature_2m_max,temperature_2m_min,weathercode,precipitation_probability_max",
                "timezone": "auto",
                "forecast_days": min(max(days, 1), 14),
            })
            url = f"https://api.open-meteo.com/v1/forecast?{params}"
            st, raw = self.t("GET", url, {"User-Agent": "TravelMindAI/1.0"}, None, self.timeout)
            if st != 200:
                return ProviderResult(self.name, "error", None, f"Open-Meteo returned HTTP {st}")

            payload = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
            daily = payload.get("daily", {})
            times = daily.get("time", [])
            max_temps = daily.get("temperature_2m_max", [])
            min_temps = daily.get("temperature_2m_min", [])
            codes = daily.get("weathercode", [])
            rain_probs = daily.get("precipitation_probability_max", [])

            forecast_days = []
            for i in range(len(times)):
                code = codes[i] if i < len(codes) else 0
                forecast_days.append({
                    "date": times[i],
                    "temp_max_c": max_temps[i] if i < len(max_temps) else None,
                    "temp_min_c": min_temps[i] if i < len(min_temps) else None,
                    "condition": WMO_WEATHER_CODES.get(code, "Clear"),
                    "precipitation_probability_pct": rain_probs[i] if i < len(rain_probs) else 0,
                    "weather_code": code,
                })

            data = {
                "latitude": latitude,
                "longitude": longitude,
                "timezone": payload.get("timezone", "UTC"),
                "elevation_m": payload.get("elevation", 0),
                "forecast": forecast_days,
                "source": "open-meteo-live",
            }
            return ProviderResult(self.name, "ok", data, f"Retrieved {len(forecast_days)} day forecast")
        except Exception as exc:
            return ProviderResult(self.name, "error", None, f"{type(exc).__name__}: {exc}")


def build_weather_provider(env: dict[str, Any] | None = None) -> WeatherProvider:
    # Open-Meteo works live out-of-the-box without keys
    return OpenMeteoWeatherProvider()
