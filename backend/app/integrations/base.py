"""Provider abstraction. Business logic depends on these interfaces only."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from ..core.types import ProviderResult
from .airports import format_flight_endpoint, resolve_airport

# Transport = callable(method, url, headers, body_bytes|None, timeout) -> (status, body_bytes)
Transport = Callable[[str, str, dict, Optional[bytes], float], tuple]


def urllib_transport(method, url, headers, body, timeout):
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


CITY_TO_IATA: dict[str, str] = {
    # Major International Hubs
    "LISBON": "LIS",
    "PARIS": "PAR",
    "LONDON": "LON",
    "NEW YORK": "NYC",
    "SAN FRANCISCO": "SFO",
    "TOKYO": "TYO",
    "DUBAI": "DXB",
    "ROME": "ROM",
    "ISTANBUL": "IST",
    "BARCELONA": "BCN",
    "BERLIN": "BER",
    "AMSTERDAM": "AMS",
    "MADRID": "MAD",
    "SINGAPORE": "SIN",
    "SYDNEY": "SYD",
    "TORONTO": "YTO",
    "BANGKOK": "BKK",
    "BALI": "DPS",
    "DENPASAR": "DPS",
    # Major Indian Cities & Airports
    "DELHI": "DEL",
    "NEW DELHI": "DEL",
    "MUMBAI": "BOM",
    "BOMBAY": "BOM",
    "PUNE": "PNQ",
    "BANGALORE": "BLR",
    "BENGALURU": "BLR",
    "GOA": "GOI",
    "NORTH GOA": "GOX",
    "SOUTH GOA": "GOI",
    "MOPA": "GOX",
    "DABOLIM": "GOI",
    "JAIPUR": "JAI",
    "KERALA": "COK",
    "KOCHI": "COK",
    "COCHIN": "COK",
    "CHENNAI": "MAA",
    "MADRAS": "MAA",
    "KOLKATA": "CCU",
    "CALCUTTA": "CCU",
    "HYDERABAD": "HYD",
    "UDAIPUR": "UDR",
    "VARANASI": "VNS",
    "AMRITSAR": "ATQ",
    "SRINAGAR": "SXR",
    "CHANDIGARH": "IXC",
    "MANALI": "KUU",
    "KULLU": "KUU",
    "AGRA": "AGR",
    "AHMEDABAD": "AMD",
    "LUCKNOW": "LKO",
    "GUWAHATI": "GAU",
    "PORT BLAIR": "IXZ",
    "ANDAMAN": "IXZ",
    "BAGDOGRA": "IXB",
    "DARJEELING": "IXB",
    "THIRUVANANTHAPURAM": "TRV",
    "TRIVANDRUM": "TRV",
    "NAGPUR": "NAG",
    "BHOPAL": "BHO",
    "INDORE": "IDR",
    "PATNA": "PAT",
    "RISHIKESH": "DED",
    "DEHRADUN": "DED",
}

AIRLINE_NAMES: dict[str, str] = {
    # International Carriers
    "TK": "Turkish Airlines",
    "TP": "TAP Air Portugal",
    "AF": "Air France",
    "BA": "British Airways",
    "LH": "Lufthansa",
    "UA": "United Airlines",
    "AA": "American Airlines",
    "DL": "Delta Air Lines",
    "EK": "Emirates",
    "QR": "Qatar Airways",
    "SQ": "Singapore Airlines",
    "JL": "Japan Airlines",
    "NH": "ANA",
    "IB": "Iberia",
    "KL": "KLM",
    "AZ": "ITA Airways",
    "FZ": "flydubai",
    "EY": "Etihad Airways",
    "TG": "Thai Airways",
    "MH": "Malaysia Airlines",
    "VN": "Vietnam Airlines",
    # Indian Carriers
    "AI": "Air India",
    "6E": "IndiGo",
    "UK": "Vistara",
    "QP": "Akasa Air",
    "SG": "SpiceJet",
    "IX": "Air India Express",
}


def resolve_iata(code_or_city: str) -> str:
    cleaned = code_or_city.strip().upper()
    if len(cleaned) == 3 and cleaned.isalpha():
        return cleaned
    if cleaned in CITY_TO_IATA:
        return CITY_TO_IATA[cleaned]
    # Check substring matches (e.g., "Goa, India" -> "GOA", "New Delhi" -> "DEL")
    for key, code in CITY_TO_IATA.items():
        if key in cleaned or cleaned in key:
            return code
    return cleaned[:3].upper()


class FlightProvider(ABC):
    name: str

    @abstractmethod
    def search(
        self,
        origin: str,
        destination: str,
        depart: str,
        *,
        adults: int = 1,
        currency: str = "USD",
        max_results: int = 10,
        return_date: Optional[str] = None,
    ) -> ProviderResult:
        ...


class UnconfiguredFlightProvider(FlightProvider):
    """Used when credentials are missing. Honest: returns no data, never fake offers."""

    def __init__(self, name: str = "none", reason: str = "no flight provider credentials configured"):
        self.name, self._reason = name, reason

    def search(self, *a, **k) -> ProviderResult:
        return ProviderResult(self.name, "unconfigured", None, self._reason)


class AmadeusFlightProvider(FlightProvider):
    """Amadeus Self-Service flight-offers adapter with carrier normalization and error handling."""

    name = "amadeus"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        *,
        base_url: str = "https://test.api.amadeus.com",
        transport: Transport = urllib_transport,
        timeout: float = 15.0,
    ):
        self.cid, self.secret, self.base = client_id, client_secret, base_url.rstrip("/")
        self.t, self.timeout, self._token = transport, timeout, None

    def _auth(self) -> Optional[str]:
        body = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "client_id": self.cid,
            "client_secret": self.secret,
        }).encode()
        st, raw = self.t(
            "POST",
            f"{self.base}/v1/security/oauth2/token",
            {"Content-Type": "application/x-www-form-urlencoded"},
            body,
            self.timeout,
        )
        if st != 200:
            return None
        self._token = json.loads(raw).get("access_token")
        return self._token

    def search(
        self,
        origin: str,
        destination: str,
        depart: str,
        *,
        adults: int = 1,
        currency: str = "USD",
        max_results: int = 10,
        return_date: Optional[str] = None,
    ) -> ProviderResult:
        try:
            token = self._token or self._auth()
            if not token:
                return ProviderResult(self.name, "error", None, "authentication failed")

            iata_origin = resolve_iata(origin)
            iata_dest = resolve_iata(destination)

            query_params: dict[str, Any] = {
                "originLocationCode": iata_origin,
                "destinationLocationCode": iata_dest,
                "departureDate": depart,
                "adults": adults,
                "currencyCode": currency,
                "max": max_results,
            }
            if return_date:
                query_params["returnDate"] = return_date

            q = urllib.parse.urlencode(query_params)
            st, raw = self.t(
                "GET",
                f"{self.base}/v2/shopping/flight-offers?{q}",
                {"Authorization": f"Bearer {token}"},
                None,
                self.timeout,
            )
            if st == 401:  # token expired: retry once
                self._token = None
                token = self._auth()
                st, raw = self.t(
                    "GET",
                    f"{self.base}/v2/shopping/flight-offers?{q}",
                    {"Authorization": f"Bearer {token}"},
                    None,
                    self.timeout,
                )
            if st != 200:
                return ProviderResult(self.name, "error", None, f"HTTP {st}")
            raw_json = json.loads(raw)
            dict_data = raw_json.get("dictionaries", {})
            offers = [
                self._norm(
                    o,
                    dictionaries=dict_data,
                    fallback_origin=iata_origin,
                    fallback_dest=iata_dest,
                    provider=self,
                )
                for o in raw_json.get("data", [])
            ]
            return ProviderResult(self.name, "ok", offers, f"{len(offers)} offers")
        except Exception as e:
            return ProviderResult(self.name, "error", None, f"{type(e).__name__}: {e}")

    @classmethod
    def _norm(
        cls,
        o: dict,
        dictionaries: Optional[dict[str, Any]] = None,
        fallback_origin: Optional[str] = None,
        fallback_dest: Optional[str] = None,
        provider: Optional[Any] = None,
    ) -> dict:
        it = o["itineraries"][0]
        segs = it.get("segments", [])
        if not segs:
            segs = [{}]
        first_seg = segs[0]
        last_seg = segs[-1]

        dep_obj = first_seg.get("departure", {})
        arr_obj = last_seg.get("arrival", {})

        dep_iata = dep_obj.get("iataCode") or fallback_origin or "DEP"
        arr_iata = arr_obj.get("iataCode") or fallback_dest or "ARR"

        dep_time = dep_obj.get("at")
        arr_time = arr_obj.get("at")

        dep_terminal = dep_obj.get("terminal")
        arr_terminal = arr_obj.get("terminal")

        amadeus_locs = (dictionaries or {}).get("locations", {})

        dep_info = format_flight_endpoint(
            dep_iata,
            datetime_iso=dep_time,
            terminal=dep_terminal,
            amadeus_locations=amadeus_locs,
            amadeus_provider=provider,
            is_departure=True,
        )
        arr_info = format_flight_endpoint(
            arr_iata,
            datetime_iso=arr_time,
            terminal=arr_terminal,
            amadeus_locations=amadeus_locs,
            amadeus_provider=provider,
            is_departure=False,
        )

        carrier_codes = sorted({s.get("carrierCode") for s in segs if s.get("carrierCode")})
        carrier_dict = (dictionaries or {}).get("carriers", {})
        carrier_names = [carrier_dict.get(c) or AIRLINE_NAMES.get(c, c) for c in carrier_codes]

        price_obj = o.get("price", {})
        total_price = float(price_obj.get("grandTotal", price_obj.get("total", 0.0)))
        currency = price_obj.get("currency", "USD")

        first_cabin = None
        traveler_pricings = o.get("travelerPricings")
        if traveler_pricings and isinstance(traveler_pricings, list) and len(traveler_pricings) > 0:
            fare_details = traveler_pricings[0].get("fareDetailsBySegment")
            if fare_details and isinstance(fare_details, list) and len(fare_details) > 0:
                first_cabin = fare_details[0].get("cabin")

        carrier_code = first_seg.get("carrierCode", "")
        flight_num = first_seg.get("number", "")
        flight_number = f"{carrier_code}-{flight_num}" if carrier_code and flight_num else None

        return {
            "provider_ref": o.get("id"),
            "flight_number": flight_number,
            "cabin_class": first_cabin,
            "price": total_price,
            "currency": currency,
            "duration": it.get("duration"),
            "stops": max(len(segs) - 1, 0),
            "departs": dep_time,
            "arrives": arr_time,
            "departure": dep_info,
            "arrival": arr_info,
            "departure_airport_name": dep_info["airport_name"],
            "departure_airport_iata": dep_info["airport_iata"],
            "departure_terminal": dep_info["terminal"],
            "departure_city": dep_info["city"],
            "departure_country": dep_info["country"],
            "departure_datetime": dep_time,
            "arrival_airport_name": arr_info["airport_name"],
            "arrival_airport_iata": arr_info["airport_iata"],
            "arrival_terminal": arr_info["terminal"],
            "arrival_city": arr_info["city"],
            "arrival_country": arr_info["country"],
            "arrival_datetime": arr_time,
            "carriers": carrier_codes,
            "carrier_names": carrier_names,
            "source": "amadeus-live-search",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        }


def build_flight_provider(env: dict | None = None) -> FlightProvider:
    merged_env = {**os.environ, **(env or {})}
    cid = merged_env.get("AMADEUS_CLIENT_ID")
    sec = merged_env.get("AMADEUS_CLIENT_SECRET")
    if cid and sec:
        return AmadeusFlightProvider(
            cid,
            sec,
            base_url=merged_env.get("AMADEUS_BASE_URL", "https://test.api.amadeus.com"),
        )
    return UnconfiguredFlightProvider("amadeus", "AMADEUS_CLIENT_ID / AMADEUS_CLIENT_SECRET not set")
