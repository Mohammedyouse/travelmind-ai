from .base import (
    AmadeusFlightProvider,
    FlightProvider,
    UnconfiguredFlightProvider,
    build_flight_provider,
    resolve_iata,
)
from .airports import VERIFIED_AIRPORTS, format_flight_endpoint, resolve_airport
from .currency import CurrencyProvider, OpenExchangeCurrencyProvider, build_currency_provider
from .hotels import DirectoryHotelProvider, HotelProvider, UnconfiguredHotelProvider, build_hotel_provider
from .places import HybridPlacesProvider, PlacesProvider, build_places_provider
from .providers import (
    EmailProvider,
    MapProvider,
    WhatsAppProvider,
    build_providers,
)
from .weather import OpenMeteoWeatherProvider, WeatherProvider, build_weather_provider

# Compatibility aliases
PlaceProvider = PlacesProvider

__all__ = [
    "AmadeusFlightProvider",
    "FlightProvider",
    "UnconfiguredFlightProvider",
    "build_flight_provider",
    "resolve_iata",
    "CurrencyProvider",
    "OpenExchangeCurrencyProvider",
    "build_currency_provider",
    "HotelProvider",
    "DirectoryHotelProvider",
    "UnconfiguredHotelProvider",
    "build_hotel_provider",
    "PlacesProvider",
    "PlaceProvider",
    "HybridPlacesProvider",
    "build_places_provider",
    "WeatherProvider",
    "OpenMeteoWeatherProvider",
    "build_weather_provider",
    "EmailProvider",
    "MapProvider",
    "WhatsAppProvider",
    "build_providers",
]
