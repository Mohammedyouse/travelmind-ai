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

    def test_stripe_checkout_and_webhook_event(self):
        token, _ = self.register_user("StripeUser")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Test checkout session creation
        checkout_res = self.client.post("/api/v1/payments/checkout", headers=headers, json={"tier": "pro"})
        self.assertEqual(checkout_res.status_code, 200)
        cdata = checkout_res.json()
        self.assertTrue(cdata["session_id"].startswith("cs_test_"))
        self.assertIn("checkout.stripe.com/test", cdata["checkout_url"])

        # 2. Test webhook receiver with metadata user_id & tier
        me = self.client.get("/api/v1/auth/me", headers=headers).json()
        user_id = me["user"]["sub"]
        webhook_payload = {
            "id": f"evt_test_{uuid.uuid4()}",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": f"cs_test_{uuid.uuid4()}",
                    "client_reference_id": user_id,
                    "amount_total": 1499,
                    "currency": "usd",
                    "metadata": {"tier": "pro", "user_id": user_id},
                }
            }
        }
        webhook_res = self.client.post("/api/v1/payments/webhook", json=webhook_payload)
        self.assertEqual(webhook_res.status_code, 200)
        self.assertEqual(webhook_res.json()["received"], True)

        # 3. Verify user subscription updated to Pro and received notification
        updated_me = self.client.get("/api/v1/auth/me", headers=headers).json()
        self.assertEqual(updated_me["subscription"]["tier"], "pro")

        notifs = self.client.get("/api/v1/notifications", headers=headers).json()
        self.assertTrue(any("Upgraded to Pro" in n.get("title", "") for n in notifs))

    def test_unconfigured_providers_honest_fallbacks(self):
        token, _ = self.register_user("FallbackUser")
        headers = {"Authorization": f"Bearer {token}"}

        # Plan a trip with unconfigured external API keys
        trip_res = self.client.post("/api/v1/trips", headers=headers, json={
            "origin": "NYC",
            "destination": "PAR",
            "departure_date": "2027-06-01",
            "return_date": "2027-06-06",
            "budget": 3500,
            "currency": "USD",
            "travelers": 2,
        })
        self.assertEqual(trip_res.status_code, 200)
        tdata = trip_res.json()
        results = tdata.get("agent_results") or tdata.get("plan_results") or {}

        # Flight intelligence must report honest unconfigured status without crashing
        flight_data = results["flight_intelligence"]["data"]
        self.assertEqual(flight_data["provider_status"], "unconfigured")
        self.assertIn("google.com/travel/flights", flight_data["direct_search_url"])
        self.assertEqual(flight_data["total_offers"], 0)

        # Accommodations must report verified properties with reference rate tag
        hotels = results["accommodation_intelligence"]["data"]["hotels"]
        self.assertTrue(len(hotels) > 0)
        self.assertIn("pricing_type", hotels[0])

        # Itinerary Compiler must have synthesized days without error
        itinerary = results["itinerary"]
        self.assertTrue(len(itinerary["days"]) >= 4)
        self.assertEqual(results["itinerary_compiler"]["status"], "ok")


if __name__ == "__main__":
    unittest.main()
