import unittest
import uuid

try:
    from fastapi.testclient import TestClient
    from backend.app.api.app import app as api_app
except ImportError:
    TestClient = None
    api_app = None


@unittest.skipUnless(TestClient is not None and api_app is not None, "FastAPI and TestClient required")
class TestSaaSAndN8NIntegration(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(api_app)
        self.n8n_headers = {
            "Content-Type": "application/json",
            "X-N8N-Webhook-Secret": "travelmind-n8n-secret",
        }

    def register_user(self, name: str, role: str = "traveler"):
        email = f"{name.lower()}-{uuid.uuid4()}@example.test"
        res = self.client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "Password123!",
            "full_name": name,
            "role": role,
        })
        self.assertEqual(res.status_code, 200)
        return res.json()["token"], email

    def test_n8n_unauthorized_without_secret(self):
        res = self.client.post("/api/v1/n8n/dispatch/research", json={
            "origin": "SFO", "destination": "LIS", "budget": 3000, "duration_days": 5, "currency": "USD"
        })
        self.assertEqual(res.status_code, 401)

    def test_n8n_dispatch_and_deduplication(self):
        corr_id = f"corr-test-{uuid.uuid4()}"
        headers = {**self.n8n_headers, "X-Correlation-ID": corr_id}
        payload = {
            "origin": "SFO",
            "destination": "LIS",
            "departure_date": "2027-05-10",
            "return_date": "2027-05-15",
            "budget": 3000,
            "currency": "USD",
            "travelers": 2,
        }
        res1 = self.client.post("/api/v1/n8n/dispatch/research", headers=headers, json=payload)
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res1.json()["status"], "ok")
        self.assertIn("itinerary", res1.json()["results"])

        # Second request with same correlation ID should be flagged as duplicate
        res2 = self.client.post("/api/v1/n8n/dispatch/research", headers=headers, json=payload)
        self.assertEqual(res2.status_code, 200)
        self.assertIn("duplicate", res2.json()["message"].lower())

    def test_n8n_research_sub_endpoints(self):
        # Flight search
        flight_res = self.client.post("/api/v1/n8n/flights/search", headers=self.n8n_headers, json={
            "origin": "SFO", "destination": "LIS", "departureDate": "2027-05-10", "adults": 1
        })
        self.assertEqual(flight_res.status_code, 200)

        # Hotel search
        hotel_res = self.client.post("/api/v1/n8n/hotels/search", headers=self.n8n_headers, json={
            "destination": "Lisbon", "checkIn": "2027-05-10", "checkOut": "2027-05-15"
        })
        self.assertEqual(hotel_res.status_code, 200)
        self.assertTrue(len(hotel_res.json()["hotels"]) > 0)

        # Destination discovery
        dest_res = self.client.post("/api/v1/n8n/destinations/discover", headers=self.n8n_headers, json={
            "destination": "Lisbon"
        })
        self.assertEqual(dest_res.status_code, 200)
        self.assertTrue(len(dest_res.json()["places"]) > 0)

    def test_subscription_tiers_and_quota_enforcement(self):
        token, _ = self.register_user("QuotaTester")
        headers = {"Authorization": f"Bearer {token}"}

        # Check initial subscription is Free
        me = self.client.get("/api/v1/auth/me", headers=headers).json()
        self.assertEqual(me["subscription"]["tier"], "free")
        self.assertEqual(me["quota"]["max_trips"], 3)

        # Upgrade subscription to Pro
        upgrade = self.client.post("/api/v1/subscriptions/upgrade", headers=headers, json={"tier": "pro"})
        self.assertEqual(upgrade.status_code, 200)
        self.assertEqual(upgrade.json()["tier"], "pro")

    def test_trip_export_html_and_json(self):
        token, _ = self.register_user("Exporter")
        headers = {"Authorization": f"Bearer {token}"}

        trip = self.client.post("/api/v1/trips", headers=headers, json={
            "origin": "SFO", "destination": "LIS", "departure_date": "2027-06-01",
            "return_date": "2027-06-05", "budget": 2800, "currency": "USD"
        }).json()
        trip_id = trip["id"]

        # Export JSON
        res_json = self.client.get(f"/api/v1/trips/{trip_id}/export?format=json", headers=headers)
        self.assertEqual(res_json.status_code, 200)
        self.assertEqual(res_json.json()["destination"], "LIS")

        # Export HTML
        res_html = self.client.get(f"/api/v1/trips/{trip_id}/export?format=html", headers=headers)
        self.assertEqual(res_html.status_code, 200)
        self.assertIn("<!DOCTYPE html>", res_html.text)
        self.assertIn("TravelMind AI Itinerary", res_html.text)

    def test_chat_conversations(self):
        token, _ = self.register_user("Chatter")
        headers = {"Authorization": f"Bearer {token}"}

        # Send a message
        post_msg = self.client.post("/api/v1/conversations", headers=headers, json={
            "content": "Can you help me optimize my budget for flights?"
        })
        self.assertEqual(post_msg.status_code, 200)

        # Retrieve conversation history
        convs = self.client.get("/api/v1/conversations", headers=headers).json()
        self.assertTrue(len(convs) >= 2)  # User message + assistant reply

    def test_notifications_read_flow(self):
        token, _ = self.register_user("NotifUser")
        headers = {"Authorization": f"Bearer {token}"}

        notifs = self.client.get("/api/v1/notifications", headers=headers).json()
        self.assertTrue(len(notifs) >= 1)
        notif_id = notifs[0]["id"]

        mark_res = self.client.patch(f"/api/v1/notifications/{notif_id}/read", headers=headers)
        self.assertEqual(mark_res.status_code, 200)
        self.assertEqual(mark_res.json()["status"], "read")

    def test_admin_dashboard_protection(self):
        token, _ = self.register_user("RegularUser", role="traveler")
        headers = {"Authorization": f"Bearer {token}"}

        # Regular user denied admin access
        res = self.client.get("/api/v1/admin/stats", headers=headers)
        self.assertEqual(res.status_code, 403)


if __name__ == "__main__":
    unittest.main()
