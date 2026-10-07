import unittest

from backend.app.agents import build_agent_registry
from backend.app.core.types import TripSpec
from backend.app.services.trip_service import TripService


class TestAgents(unittest.TestCase):
    def test_registry_has_required_agents(self):
        registry = build_agent_registry()
        required = {
            "travel_concierge",
            "flight_intelligence",
            "accommodation_intelligence",
            "destination_discovery",
            "transportation_route",
            "budget_intelligence",
            "personalization_recommendation",
            "travel_support",
        }
        self.assertTrue(required.issubset(set(registry)))

    def test_trip_service_handles_complete_trip(self):
        trip_spec = TripSpec.from_dict({
            "origin": "DEL",
            "destination": "PAR",
            "budget": 2500,
            "currency": "USD",
            "travelers": 2,
            "duration_days": 5,
            "interests": ["food", "culture"],
        })
        result = TripService().plan_trip(trip_spec)
        self.assertEqual(result.summary.startswith("Trip from DEL to PAR"), True)
        self.assertEqual(result.missing_fields, [])

    def test_trip_service_requests_missing_fields(self):
        result = TripService().plan_trip(TripSpec.from_dict({"origin": "DEL", "destination": "PAR"}))
        self.assertTrue(result.missing_fields)


if __name__ == "__main__":
    unittest.main()
