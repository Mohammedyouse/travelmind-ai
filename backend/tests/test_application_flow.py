import unittest
import uuid

from backend.app.core.types import TripSpec
from backend.app.db import create_trip, get_trip, init_db
from backend.app.services.trip_service import TripService

try:
    from fastapi.testclient import TestClient
    from backend.app.api.app import app as api_app
except ImportError:
    TestClient = None
    api_app = None


class TestPlanningPersistence(unittest.TestCase):
    def setUp(self):
        init_db()

    def test_all_agents_budget_and_itinerary_are_saved(self):
        spec = TripSpec.from_dict({
            "origin": "SFO",
            "destination": "LIS",
            "departure_date": "2027-05-10",
            "return_date": "2027-05-15",
            "travelers": 2,
            "budget": 3200,
            "currency": "USD",
            "interests": ["food", "architecture"],
        })
        plan = TripService().plan_trip(spec)
        expected_agents = {
            "travel_concierge", "flight_intelligence", "accommodation_intelligence",
            "destination_discovery", "transportation_route", "budget_intelligence",
            "personalization_recommendation", "travel_support",
        }
        self.assertTrue(expected_agents.issubset(plan.results))
        self.assertEqual(len(plan.results["itinerary"]["days"]), 5)
        budget = plan.results["budget_intelligence"]
        self.assertEqual(budget["status"], "ok")
        self.assertEqual(budget["data"]["source"], "development_estimate")
        self.assertIn("flights", budget["data"]["items"])

        user_id = str(uuid.uuid4())
        from backend.app.db import create_user
        create_user(f"{user_id}@example.test", "unused-test-hash", "Planner")
        from backend.app.db import get_user_by_email
        owner = get_user_by_email(f"{user_id}@example.test")
        saved = create_trip(owner["id"], {
            **spec.to_dict(),
            "status": "draft",
            "summary": plan.summary,
            "preferences": {"interests": spec.interests},
            "plan_results": plan.results,
        })
        restored = get_trip(saved["id"])
        self.assertEqual(restored["plan_results"]["budget_intelligence"]["data"]["source"], "development_estimate")
        self.assertEqual(restored["plan_results"]["itinerary"]["days"][-1]["day"], 5)


@unittest.skipUnless(TestClient is not None and api_app is not None, "FastAPI and its test client are not installed")
class TestAuthenticatedApiJourney(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(api_app)

    def register(self, name: str):
        email = f"{name}-{uuid.uuid4()}@example.test"
        response = self.client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "TravelMind123!",
            "full_name": name,
            "role": "admin",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["role"], "traveler")
        return email, response.json()["token"]

    def test_register_login_protect_create_retrieve_and_modify_trip(self):
        email, token = self.register("Taylor")
        headers = {"Authorization": f"Bearer {token}"}
        self.assertEqual(self.client.get("/api/v1/trips").status_code, 401)
        preflight = self.client.options("/api/v1/trips", headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        })
        self.assertEqual(preflight.status_code, 200)
        self.assertEqual(preflight.headers["access-control-allow-origin"], "http://127.0.0.1:5173")
        login = self.client.post("/api/v1/auth/login", json={"email": email, "password": "TravelMind123!"})
        self.assertEqual(login.status_code, 200)
        self.assertEqual(self.client.get("/api/v1/auth/me", headers=headers).json()["user"]["email"], email.lower())

        created = self.client.post("/api/v1/trips", headers=headers, json={
            "origin": "SFO",
            "destination": "LIS",
            "departure_date": "2027-05-10",
            "return_date": "2027-05-15",
            "travelers": 2,
            "budget": 3200,
            "currency": "USD",
            "interests": ["food", "architecture"],
            "preferences": {},
        })
        self.assertEqual(created.status_code, 200, created.text)
        trip_id = created.json()["id"]
        self.assertEqual(len(created.json()["plan_results"]["itinerary"]["days"]), 5)
        self.assertEqual(created.json()["plan_results"]["budget_intelligence"]["data"]["source"], "development_estimate")

        modified = self.client.patch(f"/api/v1/trips/{trip_id}", headers=headers, json={"budget": 4000, "interests": ["food", "museums"]})
        self.assertEqual(modified.status_code, 200, modified.text)
        self.assertEqual(modified.json()["budget"], 4000)
        self.assertEqual(modified.json()["preferences"]["interests"], ["food", "museums"])
        retrieved = self.client.get(f"/api/v1/trips/{trip_id}", headers=headers)
        self.assertEqual(retrieved.json()["budget"], 4000)

        _, other_token = self.register("Morgan")
        hidden = self.client.get(f"/api/v1/trips/{trip_id}", headers={"Authorization": f"Bearer {other_token}"})
        self.assertEqual(hidden.status_code, 404)


if __name__ == "__main__":
    unittest.main()