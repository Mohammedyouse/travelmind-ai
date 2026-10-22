import os
import time
import unittest
from fastapi.testclient import TestClient

from backend.app.api.app import create_app
from backend.app.auth import issue_token, register_user, authenticate_user
from backend.app.db import init_db

class TestAuthAndSessionFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        app = create_app()
        cls.client = TestClient(app)

    def test_01_successful_login(self):
        email = f"test_login_{int(time.time())}@example.com"
        register_user(email, "Password123!", "Test User", "traveler")
        
        response = self.client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("token", data)
        self.assertIn("user", data)
        self.assertEqual(data["user"]["email"], email.lower())

    def test_02_invalid_credentials(self):
        response = self.client.post("/api/v1/auth/login", json={"email": "nonexistent@example.com", "password": "WrongPassword"})
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertIn("detail", data)

    def test_03_expired_or_invalid_token(self):
        # 1. Completely invalid token
        response = self.client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid.fake.token"})
        self.assertEqual(response.status_code, 401)
        self.assertIn("detail", response.json())

        # 2. Missing bearer prefix
        response = self.client.get("/api/v1/auth/me", headers={"Authorization": "invalid.fake.token"})
        self.assertEqual(response.status_code, 401)

        # 3. Expired token (create a token with exp in the past)
        email = f"test_exp_{int(time.time())}@example.com"
        user = register_user(email, "Password123!", "Expired User", "traveler")
        
        # Build an expired token manually using issue_token logic with exp in past
        from backend.app.auth import _b64url_encode, _secret
        import json, hmac, hashlib
        now = int(time.time()) - 3600 # 1 hour ago
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "sub": user["id"],
            "email": user["email"],
            "role": user.get("role", "traveler"),
            "iat": now - 3600,
            "exp": now, # already expired
        }
        h_seg = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        p_seg = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        sig = hmac.new(_secret().encode("utf-8"), f"{h_seg}.{p_seg}".encode("utf-8"), hashlib.sha256).digest()
        expired_token = f"{h_seg}.{p_seg}.{_b64url_encode(sig)}"

        resp_exp = self.client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
        self.assertEqual(resp_exp.status_code, 401)
        self.assertIn("invalid or expired token", resp_exp.json()["detail"])

    def test_04_profile_loading(self):
        email = f"test_prof_{int(time.time())}@example.com"
        user = register_user(email, "Password123!", "Profile User", "traveler")
        token = issue_token(user)

        response = self.client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("user", data)
        self.assertIn("subscription", data)
        self.assertIn("quota", data)
        self.assertEqual(data["user"]["email"], email.lower())

    def test_05_health_check_available(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "ok")

if __name__ == "__main__":
    unittest.main()
