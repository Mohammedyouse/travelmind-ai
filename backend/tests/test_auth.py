import unittest
import uuid

from backend.app.auth import authenticate_user, hash_password, issue_token, register_user, verify_token
from backend.app.db import init_db, create_trip, list_trips


class TestAuthAndPersistence(unittest.TestCase):
    def setUp(self):
        init_db()

    def test_password_hashing_and_registration(self):
        email = f"alice-{uuid.uuid4()}@example.com"
        user = register_user(email, "Password123!", "Alice")
        self.assertEqual(user["email"], email)
        self.assertEqual(user["role"], "traveler")
        self.assertNotEqual(user["password_hash"], "Password123!")
        self.assertTrue(hash_password("Password123!") != hash_password("Password123!"))

    def test_login_requires_valid_credentials(self):
        email = f"bob-{uuid.uuid4()}@example.com"
        register_user(email, "Secret123!", "Bob")
        self.assertIsNotNone(authenticate_user(email, "Secret123!"))
        with self.assertRaises(ValueError):
            authenticate_user(email, "WrongPass!")

    def test_token_round_trip(self):
        email = f"charlie-{uuid.uuid4()}@example.com"
        user = register_user(email, "Pass123!", "Charlie", role="admin")
        token = issue_token(user)
        payload = verify_token(token)
        self.assertEqual(payload["sub"], user["id"])
        self.assertEqual(payload["role"], "admin")

    def test_trip_persistence(self):
        email = f"dana-{uuid.uuid4()}@example.com"
        user = register_user(email, "Pass123!", "Dana")
        trip = create_trip(user["id"], {
            "origin": "DXB",
            "destination": "LHR",
            "budget": 2100,
            "currency": "USD",
            "status": "draft",
        })
        trips = list_trips(user["id"])
        self.assertEqual(len(trips), 1)
        self.assertEqual(trips[0]["destination"], "LHR")
        self.assertEqual(trip["status"], "draft")


if __name__ == "__main__":
    unittest.main()
