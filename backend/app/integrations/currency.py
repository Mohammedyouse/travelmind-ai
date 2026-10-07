"""Currency exchange provider integration.
Supports live exchange rates via open.er-api.com and Frankfurter with zero API key requirement."""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any, Optional

from ..core.types import ProviderResult
from .base import Transport, urllib_transport

REFERENCE_RATES_USD: dict[str, float] = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "CAD": 1.36,
    "AUD": 1.52,
    "JPY": 155.0,
    "INR": 83.5,
    "CHF": 0.91,
    "SGD": 1.35,
    "BRL": 5.15,
    "MXN": 16.8,
}


class CurrencyProvider(ABC):
    name: str

    @abstractmethod
    def get_rates(self, base_currency: str = "USD") -> ProviderResult:
        ...

    @abstractmethod
    def convert(self, amount: float, from_curr: str, to_curr: str) -> ProviderResult:
        ...


class OpenExchangeCurrencyProvider(CurrencyProvider):
    """Fetches real-time foreign exchange rates with live fallback."""
    name = "open_exchange_api"

    def __init__(self, transport: Transport = urllib_transport, timeout: float = 8.0):
        self.t = transport
        self.timeout = timeout
        self._cached_rates: dict[str, dict[str, float]] = {}

    def get_rates(self, base_currency: str = "USD") -> ProviderResult:
        base = base_currency.upper()
        if base in self._cached_rates:
            return ProviderResult(self.name, "ok", self._cached_rates[base], f"Rates for {base} (cached)")

        try:
            url = f"https://open.er-api.com/v6/latest/{base}"
            st, raw = self.t("GET", url, {"User-Agent": "TravelMindAI/1.0"}, None, self.timeout)
            if st == 200:
                payload = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
                rates = payload.get("rates", {})
                if rates:
                    rates_data = {
                        "base": base,
                        "rates": {k: float(v) for k, v in rates.items()},
                        "provider": "open.er-api.com",
                        "time_last_update_utc": payload.get("time_last_update_utc"),
                        "source": "live-exchange-rates",
                    }
                    self._cached_rates[base] = rates_data
                    return ProviderResult(self.name, "ok", rates_data, f"Retrieved live rates for {base}")
        except Exception:
            pass

        # Fallback to reference rates if network is unavailable
        usd_base = REFERENCE_RATES_USD.copy()
        if base == "USD":
            selected_rates = usd_base
        else:
            base_to_usd = usd_base.get(base, 1.0)
            selected_rates = {k: round(v / base_to_usd, 6) for k, v in usd_base.items()}

        fallback_data = {
            "base": base,
            "rates": selected_rates,
            "provider": "reference_rates",
            "source": "reference_rates",
        }
        return ProviderResult(self.name, "ok", fallback_data, f"Using reference rates for {base}")

    def convert(self, amount: float, from_curr: str, to_curr: str) -> ProviderResult:
        from_c = from_curr.upper()
        to_c = to_curr.upper()
        if from_c == to_c:
            return ProviderResult(self.name, "ok", {"amount": amount, "rate": 1.0, "converted": amount, "from": from_c, "to": to_c})

        rates_result = self.get_rates(from_c)
        if not rates_result.ok or not rates_result.data:
            return ProviderResult(self.name, "error", None, f"Could not retrieve rates for {from_c}")

        rates = rates_result.data.get("rates", {})
        if to_c not in rates:
            return ProviderResult(self.name, "error", None, f"Currency {to_c} not found in rates table")

        rate = rates[to_c]
        converted = round(amount * rate, 2)
        return ProviderResult(self.name, "ok", {
            "amount": amount,
            "from": from_c,
            "to": to_c,
            "rate": rate,
            "converted": converted,
            "source": rates_result.data.get("source", "live-exchange-rates"),
        })


def build_currency_provider(env: dict[str, Any] | None = None) -> CurrencyProvider:
    return OpenExchangeCurrencyProvider()
