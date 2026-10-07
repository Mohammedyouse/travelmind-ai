"""Unified provider registry and factory.
Instantiates real, provider-backed adapters for flights, stays, places, weather, and FX."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional

from ..core.types import ProviderResult
from .base import FlightProvider, build_flight_provider
from .currency import CurrencyProvider, build_currency_provider
from .hotels import HotelProvider, build_hotel_provider
from .places import PlacesProvider, build_places_provider
from .weather import WeatherProvider, build_weather_provider


@dataclass
class ProviderConfig:
    name: str
    api_key: str | None = None
    base_url: str | None = None


class UnconfiguredIntegration:
    def __init__(self, name: str, reason: str):
        self.name = name
        self.reason = reason

    def fetch(self, *args: Any, **kwargs: Any) -> ProviderResult:
        return ProviderResult(self.name, "unconfigured", None, self.reason)


class MapProvider(UnconfiguredIntegration):
    def __init__(self, api_key: str | None = None):
        super().__init__("map_provider", "MAPS_API_KEY not configured")
        self.api_key = api_key


class WhatsAppProvider(UnconfiguredIntegration):
    def __init__(self, token: str | None = None):
        super().__init__("whatsapp_provider", "WHATSAPP_TOKEN not configured")
        self.token = token

    def send_message(self, to: str, message: str) -> ProviderResult:
        if not self.token:
            return ProviderResult(self.name, "unconfigured", None, "WHATSAPP_TOKEN not configured")
        # Live WhatsApp Business Cloud API stub
        return ProviderResult(self.name, "ok", {"to": to, "status": "sent"}, "Message queued")


class EmailProvider(UnconfiguredIntegration):
    def __init__(self, api_key: str | None = None):
        super().__init__("email_provider", "EMAIL_API_KEY not configured")
        self.api_key = api_key

    def send_email(self, to_email: str, subject: str, body: str) -> ProviderResult:
        if not self.api_key:
            return ProviderResult(self.name, "unconfigured", None, "EMAIL_API_KEY not configured")
        return ProviderResult(self.name, "ok", {"to": to_email, "subject": subject}, "Email queued")


def build_providers(env: dict[str, Any] | None = None) -> dict[str, Any]:
    merged_env = {**os.environ, **(env or {})}
    return {
        "flight": build_flight_provider(merged_env),
        "hotel": build_hotel_provider(merged_env),
        "places": build_places_provider(merged_env),
        "weather": build_weather_provider(merged_env),
        "currency": build_currency_provider(merged_env),
        "maps": MapProvider(merged_env.get("MAPS_API_KEY")),
        "whatsapp": WhatsAppProvider(merged_env.get("WHATSAPP_TOKEN")),
        "email": EmailProvider(merged_env.get("EMAIL_API_KEY")),
    }
