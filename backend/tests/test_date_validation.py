from datetime import date, datetime, timedelta, timezone
import unittest
from fastapi.testclient import TestClient

from backend.app.core.types import TripSpec, ValidationError
from backend.app.api.app import app


class TestDateValidation(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_date_validation_yesterday_rejected(self):
        today = datetime.now(timezone.utc).date()
        yesterday = today - timedelta(days=1)
        
        with self.assertRaises(ValueError) as ctx:
            TripSpec(
                origin="DEL",
                destination="BOM",
                departure_date=yesterday,
                duration_days=3,
            )
        self.assertIn("cannot be in the past", str(ctx.exception))

    def test_date_validation_today_accepted(self):
        today = datetime.now(timezone.utc).date()
        spec = TripSpec(
            origin="DEL",
            destination="BOM",
            departure_date=today,
            duration_days=3,
        )
        self.assertEqual(spec.departure_date, today)
        self.assertEqual(spec.return_date, today + timedelta(days=3))

    def test_date_validation_tomorrow_accepted(self):
        today = datetime.now(timezone.utc).date()
        tomorrow = today + timedelta(days=1)
        spec = TripSpec(
            origin="DEL",
            destination="BOM",
            departure_date=tomorrow,
            return_date=tomorrow + timedelta(days=2),
        )
        self.assertEqual(spec.departure_date, tomorrow)
        self.assertEqual(spec.duration_days, 2)

    def test_return_date_before_departure_rejected(self):
        today = datetime.now(timezone.utc).date()
        departure = today + timedelta(days=5)
        invalid_return = today + timedelta(days=2)
        
        with self.assertRaises(ValueError) as ctx:
            TripSpec(
                origin="DEL",
                destination="BOM",
                departure_date=departure,
                return_date=invalid_return,
            )
        self.assertIn("cannot be before departure date", str(ctx.exception))

    def test_same_day_return_accepted(self):
        today = datetime.now(timezone.utc).date()
        departure = today + timedelta(days=3)
        spec = TripSpec(
            origin="DEL",
            destination="BOM",
            departure_date=departure,
            return_date=departure,
        )
        self.assertEqual(spec.departure_date, departure)
        self.assertEqual(spec.return_date, departure)
        self.assertEqual(spec.duration_days, 1)

    def test_inconsistent_duration_rejected(self):
        today = datetime.now(timezone.utc).date()
        departure = today + timedelta(days=2)
        return_date = today + timedelta(days=5)  # 3 days difference
        
        with self.assertRaises(ValueError) as ctx:
            TripSpec(
                origin="DEL",
                destination="BOM",
                departure_date=departure,
                return_date=return_date,
                duration_days=10,  # Doesn't match 3 days
            )
        self.assertIn("Inconsistent duration", str(ctx.exception))

    def test_invalid_date_format_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            TripSpec.from_dict({
                "origin": "DEL",
                "destination": "BOM",
                "departure_date": "not-a-valid-date",
            })
        self.assertIn("not an ISO date", str(ctx.exception))

    def test_unknown_fields_strict_rejection(self):
        """Strict validation test: arbitrary unknown fields are strictly rejected by TripSpec.from_dict."""
        with self.assertRaises(ValidationError) as ctx:
            TripSpec.from_dict({
                "origin": "DEL",
                "destination": "BOM",
                "budget": 2000,
                "currency": "USD",
                "unrecognized_custom_field": "test_value",
            })
        self.assertIn("unknown fields: ['unrecognized_custom_field']", str(ctx.exception))

    def test_client_date_accepted_and_validated(self):
        """client_date is a recognized ISO date field in TripSpec contract used for timezone-aware validation."""
        today = datetime.now(timezone.utc).date()
        future_dep = today + timedelta(days=5)
        spec = TripSpec.from_dict({
            "origin": "DEL",
            "destination": "BOM",
            "departure_date": future_dep.isoformat(),
            "budget": 2000,
            "currency": "USD",
            "client_date": today.isoformat(),
        })
        self.assertEqual(spec.client_date, today)

    def test_identical_origin_and_destination_rejected(self):
        """TripSpec rejects identical origin and destination (e.g. DEL to DEL)."""
        today = datetime.now(timezone.utc).date()
        with self.assertRaises(ValueError) as ctx:
            TripSpec(
                origin="DELHI",
                destination="DELHI",
                departure_date=today + timedelta(days=2),
                budget=1500,
                currency="USD",
            )
        self.assertIn("Destination cannot be the same as origin", str(ctx.exception))

    def test_api_rejection_for_past_date_via_http(self):
        email = f"date_tester_{datetime.now().timestamp()}@example.com"
        reg_resp = self.client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "Password123!",
            "full_name": "Date Tester"
        })
        self.assertEqual(reg_resp.status_code, 200)
        token = reg_resp.json()["token"]
        
        utc_today = datetime.now(timezone.utc).date()
        yesterday = utc_today - timedelta(days=1)
        
        # Direct API request with past departure date
        resp = self.client.post(
            "/api/v1/trips",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "origin": "DEL",
                "destination": "BOM",
                "departure_date": yesterday.isoformat(),
                "travelers": 2,
                "budget": 45000,
                "currency": "INR",
            }
        )
        self.assertEqual(resp.status_code, 422)
        self.assertIn("cannot be in the past", resp.json()["detail"])

    def test_api_rejection_for_invalid_return_date_via_http(self):
        email = f"return_tester_{datetime.now().timestamp()}@example.com"
        reg_resp = self.client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "Password123!",
            "full_name": "Return Tester"
        })
        self.assertEqual(reg_resp.status_code, 200)
        token = reg_resp.json()["token"]
        
        utc_today = datetime.now(timezone.utc).date()
        dep = utc_today + timedelta(days=10)
        ret = utc_today + timedelta(days=5)
        
        resp = self.client.post(
            "/api/v1/trips",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "origin": "DEL",
                "destination": "BOM",
                "departure_date": dep.isoformat(),
                "return_date": ret.isoformat(),
                "travelers": 2,
                "budget": 45000,
                "currency": "INR",
            }
        )
        self.assertEqual(resp.status_code, 422)
        self.assertIn("cannot be before departure date", resp.json()["detail"])

    def test_api_accepts_valid_future_trip_via_http(self):
        email = f"valid_tester_{datetime.now().timestamp()}@example.com"
        reg_resp = self.client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "Password123!",
            "full_name": "Valid Tester"
        })
        self.assertEqual(reg_resp.status_code, 200)
        token = reg_resp.json()["token"]

        utc_today = datetime.now(timezone.utc).date()
        dep = utc_today + timedelta(days=14)
        ret = utc_today + timedelta(days=18)

        resp = self.client.post(
            "/api/v1/trips",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "origin": "DEL",
                "destination": "BOM",
                "departure_date": dep.isoformat(),
                "return_date": ret.isoformat(),
                "travelers": 2,
                "budget": 45000,
                "currency": "INR",
                "interests": ["food", "culture"],
                "preferences": {"travel_style": "balanced"}
            }
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["origin"], "DEL")
        self.assertEqual(data["destination"], "BOM")
        self.assertIn("summary", data)


    def test_api_rejection_for_identical_origin_destination(self):
        email = f"same_city_tester_{datetime.now().timestamp()}@example.com"
        reg_resp = self.client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "Password123!",
            "full_name": "City Tester"
        })
        self.assertEqual(reg_resp.status_code, 200)
        token = reg_resp.json()["token"]

        utc_today = datetime.now(timezone.utc).date()
        dep = utc_today + timedelta(days=10)
        resp = self.client.post(
            "/api/v1/trips",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "origin": "DELHI",
                "destination": "delhi",
                "departure_date": dep.isoformat(),
                "travelers": 2,
                "budget": 30000,
                "currency": "INR",
            }
        )
        self.assertEqual(resp.status_code, 422)
        self.assertIn("Destination cannot be the same as origin", resp.json()["detail"])

    def test_api_rejection_for_unknown_fields(self):
        email = f"unknown_field_tester_{datetime.now().timestamp()}@example.com"
        reg_resp = self.client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "Password123!",
            "full_name": "Field Tester"
        })
        self.assertEqual(reg_resp.status_code, 200)
        token = reg_resp.json()["token"]

        utc_today = datetime.now(timezone.utc).date()
        dep = utc_today + timedelta(days=10)
        resp = self.client.post(
            "/api/v1/trips",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "origin": "DEL",
                "destination": "BOM",
                "departure_date": dep.isoformat(),
                "travelers": 2,
                "budget": 30000,
                "currency": "INR",
                "unexpected_garbage_param": 9999,
            }
        )
        self.assertEqual(resp.status_code, 422)
        self.assertIn("unknown fields: ['unexpected_garbage_param']", resp.json()["detail"])

    def test_export_html_with_token_query_param(self):
        email = f"export_tester_{datetime.now().timestamp()}@example.com"
        reg_resp = self.client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "Password123!",
            "full_name": "Export Tester"
        })
        token = reg_resp.json()["token"]

        utc_today = datetime.now(timezone.utc).date()
        trip_resp = self.client.post(
            "/api/v1/trips",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "origin": "DEL",
                "destination": "VNS",
                "departure_date": (utc_today + timedelta(days=10)).isoformat(),
                "travelers": 2,
                "budget": 30000,
                "currency": "INR",
            }
        )
        trip_id = trip_resp.json()["id"]

        # Call export with token query param (browser new-window pattern) without Authorization header
        export_resp = self.client.get(f"/api/v1/trips/{trip_id}/export?format=html&token={token}")
        self.assertEqual(export_resp.status_code, 200)
        self.assertIn("TravelMind AI Itinerary", export_resp.text)
        self.assertIn("Print Itinerary", export_resp.text)

    def test_patch_trip_with_client_date_and_reschedule(self):
        """PATCH /api/v1/trips/{trip_id} accepts client_date without 422 unsupported field error and reschedules properly."""
        email = f"patch_tester_{datetime.now().timestamp()}@example.com"
        reg_resp = self.client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "Password123!",
            "full_name": "Patch Tester"
        })
        token = reg_resp.json()["token"]

        utc_today = datetime.now(timezone.utc).date()
        trip_resp = self.client.post(
            "/api/v1/trips",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "origin": "DEL",
                "destination": "BOM",
                "departure_date": (utc_today + timedelta(days=5)).isoformat(),
                "travelers": 1,
                "budget": 20000,
                "currency": "INR",
            }
        )
        self.assertEqual(trip_resp.status_code, 200)
        trip_id = trip_resp.json()["id"]

        # Now update trip with client_date included in payload
        new_dep = (utc_today + timedelta(days=12)).isoformat()
        new_ret = (utc_today + timedelta(days=16)).isoformat()
        patch_resp = self.client.patch(
            f"/api/v1/trips/{trip_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "departure_date": new_dep,
                "return_date": new_ret,
                "budget": 25000,
                "client_date": utc_today.isoformat(),
            }
        )
        self.assertEqual(patch_resp.status_code, 200)
        updated = patch_resp.json()
        self.assertEqual(updated["departure_date"], new_dep)
        self.assertEqual(updated["return_date"], new_ret)
        self.assertEqual(updated["budget"], 25000)

    def test_single_day_trip_itinerary_and_duration_days_stored(self):
        """Single day trip (same day departure and return) generates express day tour with return transfer and populates duration_days."""
        email = f"sameday_tester_{datetime.now().timestamp()}@example.com"
        reg_resp = self.client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "Password123!",
            "full_name": "Same Day Tester"
        })
        token = reg_resp.json()["token"]

        utc_today = datetime.now(timezone.utc).date()
        target_day = (utc_today + timedelta(days=7)).isoformat()
        trip_resp = self.client.post(
            "/api/v1/trips",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "origin": "DEL",
                "destination": "BOM",
                "departure_date": target_day,
                "return_date": target_day,
                "budget": 20000,
                "currency": "INR",
            }
        )
        self.assertEqual(trip_resp.status_code, 200)
        data = trip_resp.json()
        self.assertEqual(data["duration_days"], 1)
        itinerary = data["agent_results"]["itinerary"]["days"]
        self.assertEqual(len(itinerary), 1)
        day1 = itinerary[0]
        self.assertIn("Express Day Tour", day1["title"])
        self.assertIn("transfer to departure terminal", day1["evening"]["activity"])


if __name__ == "__main__":
    unittest.main()


