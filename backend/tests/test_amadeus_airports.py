"""Unit tests for verified airport resolution and Amadeus flight intelligence.
Verifies:
- complete airport info in departure and arrival (name, iata, terminal, city, country, datetime)
- no fabricated names: accurate lookup against verified airport dataset and provider dictionaries
- JFK -> CDG real-world route test
- Amadeus provider normalization and FlightIntelligenceAgent integration
"""
import json
import unittest

from backend.app.agents.flight_intelligence import FlightIntelligenceAgent
from backend.app.core.types import TripSpec
from backend.app.integrations.airports import (
    VERIFIED_AIRPORTS,
    format_flight_endpoint,
    resolve_airport,
)
from backend.app.integrations.base import AmadeusFlightProvider


class TestAirportResolution(unittest.TestCase):
    def test_jfk_resolution(self):
        jfk = resolve_airport("JFK")
        self.assertEqual(jfk["airport_iata"], "JFK")
        self.assertEqual(jfk["airport_name"], "John F. Kennedy International Airport")
        self.assertEqual(jfk["city"], "New York")
        self.assertEqual(jfk["country"], "United States")

    def test_cdg_resolution(self):
        cdg = resolve_airport("CDG")
        self.assertEqual(cdg["airport_iata"], "CDG")
        self.assertEqual(cdg["airport_name"], "Paris Charles de Gaulle Airport")
        self.assertEqual(cdg["city"], "Paris")
        self.assertEqual(cdg["country"], "France")

    def test_format_flight_endpoints_jfk_to_cdg(self):
        dep = format_flight_endpoint(
            "JFK",
            datetime_iso="2026-11-01T17:30:00",
            terminal="4",
            is_departure=True,
        )
        arr = format_flight_endpoint(
            "CDG",
            datetime_iso="2026-11-02T07:00:00",
            terminal="2E",
            is_departure=False,
        )

        # 1. airport_name
        self.assertEqual(dep["airport_name"], "John F. Kennedy International Airport")
        self.assertEqual(arr["airport_name"], "Paris Charles de Gaulle Airport")

        # 2. airport_iata
        self.assertEqual(dep["airport_iata"], "JFK")
        self.assertEqual(arr["airport_iata"], "CDG")

        # 3. terminal (when available)
        self.assertEqual(dep["terminal"], "4")
        self.assertEqual(arr["terminal"], "2E")

        # 4. city
        self.assertEqual(dep["city"], "New York")
        self.assertEqual(arr["city"], "Paris")

        # 5. country
        self.assertEqual(dep["country"], "United States")
        self.assertEqual(arr["country"], "France")

        # 6. departure/arrival datetime
        self.assertEqual(dep["departure_datetime"], "2026-11-01T17:30:00")
        self.assertEqual(dep["datetime"], "2026-11-01T17:30:00")
        self.assertEqual(arr["arrival_datetime"], "2026-11-02T07:00:00")
        self.assertEqual(arr["datetime"], "2026-11-02T07:00:00")

    def test_amadeus_flight_provider_normalizes_complete_airports(self):
        raw_offer = {
            "id": "offer-jfk-cdg-001",
            "price": {"grandTotal": "685.50", "currency": "USD"},
            "itineraries": [
                {
                    "duration": "PT7H30M",
                    "segments": [
                        {
                            "carrierCode": "AF",
                            "number": "007",
                            "departure": {
                                "iataCode": "JFK",
                                "terminal": "4",
                                "at": "2026-11-01T17:30:00",
                            },
                            "arrival": {
                                "iataCode": "CDG",
                                "terminal": "2E",
                                "at": "2026-11-02T07:00:00",
                            },
                        }
                    ],
                }
            ],
        }
        dictionaries = {
            "locations": {
                "JFK": {"cityCode": "NYC", "countryCode": "US"},
                "CDG": {"cityCode": "PAR", "countryCode": "FR"},
            },
            "carriers": {"AF": "Air France"},
        }

        norm = AmadeusFlightProvider._norm(raw_offer, dictionaries=dictionaries)

        # Check top level
        self.assertEqual(norm["price"], 685.50)
        self.assertEqual(norm["currency"], "USD")
        self.assertEqual(norm["stops"], 0)
        self.assertEqual(norm["flight_number"], "AF-007")

        # Check departure object
        dep = norm["departure"]
        self.assertEqual(dep["airport_name"], "John F. Kennedy International Airport")
        self.assertEqual(dep["airport_iata"], "JFK")
        self.assertEqual(dep["terminal"], "4")
        self.assertEqual(dep["city"], "New York")
        self.assertEqual(dep["country"], "United States")
        self.assertEqual(dep["departure_datetime"], "2026-11-01T17:30:00")

        # Check arrival object
        arr = norm["arrival"]
        self.assertEqual(arr["airport_name"], "Paris Charles de Gaulle Airport")
        self.assertEqual(arr["airport_iata"], "CDG")
        self.assertEqual(arr["terminal"], "2E")
        self.assertEqual(arr["city"], "Paris")
        self.assertEqual(arr["country"], "France")
        self.assertEqual(arr["arrival_datetime"], "2026-11-02T07:00:00")

        # Check flattened convenience fields
        self.assertEqual(norm["departure_airport_name"], "John F. Kennedy International Airport")
        self.assertEqual(norm["arrival_airport_name"], "Paris Charles de Gaulle Airport")
        self.assertEqual(norm["departure_airport_iata"], "JFK")
        self.assertEqual(norm["arrival_airport_iata"], "CDG")

    def test_flight_intelligence_agent_produces_complete_airports(self):
        agent = FlightIntelligenceAgent()
        trip_spec = TripSpec.from_dict({
            "origin": "JFK",
            "destination": "CDG",
            "departure_date": "2026-11-01",
            "return_date": "2026-11-10",
            "budget": 2000,
            "currency": "USD",
            "travelers": 1,
        })
        output = agent.run({"trip_spec": trip_spec})

        self.assertEqual(output.status, "ok")
        offers = output.data.get("offers", [])
        self.assertGreater(len(offers), 0)

        for o in offers:
            self.assertIn("departure", o)
            self.assertIn("arrival", o)

            dep = o["departure"]
            arr = o["arrival"]

            self.assertEqual(dep["airport_name"], "John F. Kennedy International Airport")
            self.assertEqual(dep["airport_iata"], "JFK")
            self.assertEqual(dep["city"], "New York")
            self.assertEqual(dep["country"], "United States")
            self.assertTrue(dep["departure_datetime"].startswith("2026-11-01"))

            self.assertEqual(arr["airport_name"], "Paris Charles de Gaulle Airport")
            self.assertEqual(arr["airport_iata"], "CDG")
            self.assertEqual(arr["city"], "Paris")
            self.assertEqual(arr["country"], "France")
            self.assertTrue(arr["arrival_datetime"].startswith("2026-11-01"))


if __name__ == "__main__":
    unittest.main()
