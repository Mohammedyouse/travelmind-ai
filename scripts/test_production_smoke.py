import urllib.request
import json
import sys
from datetime import datetime, timedelta

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROD_URL = "https://travelmind-ai-seven.vercel.app"

def run_tests():
    print(f"\n=======================================================")
    print(f"TRAVELMIND AI -- LIVE PRODUCTION SMOKE TESTS")
    print(f"Target: {PROD_URL}")
    print(f"Time: {datetime.now().isoformat()}")
    print(f"=======================================================\n")

    # 1. Health check
    print("--> TEST 1: Health check /health")
    with urllib.request.urlopen(f"{PROD_URL}/health") as r:
        assert r.status == 200
        data = json.loads(r.read().decode())
        print(f"  [PASS] Status: {r.status}, Payload: {data}")
        assert data.get("status") == "ok"

    # 2. Register new user
    print("\n--> TEST 2: User registration")
    test_id = int(datetime.now().timestamp())
    email = f"prod_tester_{test_id}@travelmind.test"
    password = "ProdPassword123!"
    reg_body = json.dumps({
        "email": email,
        "password": password,
        "full_name": "Production Smoke Tester"
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{PROD_URL}/api/v1/auth/register",
        data=reg_body,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as r:
        assert r.status == 200
        reg_data = json.loads(r.read().decode())
        token = reg_data["token"]
        user = reg_data["user"]
        print(f"  [PASS] Registered user {user['email']}, received JWT token ({len(token)} chars)")

    # 3. Protected endpoint GET /api/v1/auth/me
    print("\n--> TEST 3: Protected endpoint GET /api/v1/auth/me")
    req = urllib.request.Request(
        f"{PROD_URL}/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req) as r:
        assert r.status == 200
        me_data = json.loads(r.read().decode())
        print(f"  [PASS] Authenticated user confirmed: {me_data['user']['email']}")

    # 4. Protected endpoint GET /api/v1/preferences
    print("\n--> TEST 4: Protected endpoint GET /api/v1/preferences")
    req = urllib.request.Request(
        f"{PROD_URL}/api/v1/preferences",
        headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req) as r:
        assert r.status == 200
        prefs_data = json.loads(r.read().decode())
        print(f"  [PASS] User preferences: currency={prefs_data.get('currency')}, pace={prefs_data.get('travel_pace')}")

    # 5. Create trip & run 8-agent swarm in production
    print("\n--> TEST 5: Trip Planning & Agent Orchestration POST /api/v1/trips")
    dep_date = (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d")
    ret_date = (datetime.now() + timedelta(days=20)).strftime("%Y-%m-%d")
    client_date = datetime.now().strftime("%Y-%m-%d")

    trip_payload = json.dumps({
        "origin": "LONDON",
        "destination": "DUBAI",
        "departure_date": dep_date,
        "return_date": ret_date,
        "travelers": 2,
        "budget": 3000,
        "currency": "USD",
        "interests": ["Culture & Heritage", "Culinary & Wine", "Architecture"],
        "preferences": {"travel_style": "Balanced Explorer"},
        "client_date": client_date
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{PROD_URL}/api/v1/trips",
        data=trip_payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
    )
    with urllib.request.urlopen(req) as r:
        assert r.status == 200
        trip = json.loads(r.read().decode())
        trip_id = trip["id"]
        print(f"  [PASS] Trip generated in production! ID: {trip_id}")
        print(f"  Summary: {trip.get('summary')}")
        results = trip.get("plan_results", {})
        itinerary = results.get("itinerary", {})
        print(f"  Itinerary days count: {len(itinerary.get('days', []))}")
        hotels = results.get("accommodation_intelligence", {}).get("data", {}).get("hotels", [])
        print(f"  Hotels discovered: {len(hotels)}")
        places = results.get("destination_discovery", {}).get("data", {}).get("places", [])
        print(f"  Attractions discovered: {len(places)}")
        assert len(itinerary.get("days", [])) >= 5, "Expected at least 5 days"
        assert len(hotels) >= 5, "Expected verified hotels"
        assert len(places) >= 6, "Expected verified places"

    # 6. Trip modification (testing BUG-PATCH-CLIENT-DATE-001 in production)
    print("\n--> TEST 6: Trip modification PATCH /api/v1/trips/{id} with client_date")
    new_ret_date = (datetime.now() + timedelta(days=22)).strftime("%Y-%m-%d")
    patch_payload = json.dumps({
        "budget": 3500,
        "return_date": new_ret_date,
        "client_date": client_date
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{PROD_URL}/api/v1/trips/{trip_id}",
        data=patch_payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        },
        method="PATCH"
    )
    with urllib.request.urlopen(req) as r:
        assert r.status == 200
        updated_trip = json.loads(r.read().decode())
        print(f"  [PASS] Successfully updated trip in production! New budget: ${updated_trip.get('budget')}")

    # 7. Standalone HTML Export endpoint
    print("\n--> TEST 7: HTML Export endpoint GET /api/v1/trips/{id}/export?format=html")
    export_url = f"{PROD_URL}/api/v1/trips/{trip_id}/export?format=html&token={token}"
    with urllib.request.urlopen(export_url) as r:
        assert r.status == 200
        html = r.read().decode()
        print(f"  [PASS] Export returned HTTP 200, length: {len(html)} bytes, contains DOCTYPE: {'<!DOCTYPE html>' in html}")

    # 8. AI Assistant Chat
    print("\n--> TEST 8: AI Assistant conversation POST /api/v1/conversations")
    chat_payload = json.dumps({
        "trip_id": trip_id,
        "content": "What should I pack for Dubai in November?"
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{PROD_URL}/api/v1/conversations",
        data=chat_payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
    )
    with urllib.request.urlopen(req) as r:
        assert r.status == 200
        reply = json.loads(r.read().decode())
        print(f"  [PASS] AI Assistant reply received ({len(reply.get('content', ''))} chars): {reply.get('content', '')[:100]}...")

    # 9. Cleanup Smoke Test User
    print("\n--> CLEANUP: Safely remove smoke test account DELETE /api/v1/auth/me")
    cleanup_req = urllib.request.Request(
        f"{PROD_URL}/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        method="DELETE"
    )
    with urllib.request.urlopen(cleanup_req) as r:
        assert r.status == 200
        print("  [PASS] Smoke test account cleaned up successfully!")

    print("\n=======================================================")
    print("ALL PRODUCTION SMOKE TESTS PASSED (8/8 + CLEANUP)!")
    print("=======================================================\n")

if __name__ == "__main__":
    run_tests()
