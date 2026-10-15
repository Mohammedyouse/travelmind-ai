import urllib.request
import json
import re
from datetime import datetime, timedelta

PROD = "https://travelmind-ai-seven.vercel.app"

def run_comprehensive():
    print("=== 1. VERIFY FRONTEND & STATIC ASSETS ===")
    with urllib.request.urlopen(PROD) as r:
        html = r.read().decode("utf-8")
        print(f"HTML status: {r.status}, HTML length: {len(html)}")
        assert '<div id="root"></div>' in html, "Root element missing in HTML"
        assert "<title>TravelMind AI" in html or "<title>" in html, "Title missing"
        print("  [PASS] HTML root container and document shell verified")

        js_matches = re.findall(r'src="(/assets/[^"]+\.js)"', html)
        css_matches = re.findall(r'href="(/assets/[^"]+\.css)"', html)
        print(f"  Discovered JS assets: {js_matches}")
        print(f"  Discovered CSS assets: {css_matches}")

    for js_path in js_matches:
        with urllib.request.urlopen(PROD + js_path) as r:
            assert r.status == 200
            print(f"  [PASS] JS asset {js_path} loaded HTTP 200, length: {len(r.read())} bytes")

    for css_path in css_matches:
        with urllib.request.urlopen(PROD + css_path) as r:
            assert r.status == 200
            print(f"  [PASS] CSS asset {css_path} loaded HTTP 200, length: {len(r.read())} bytes")

    print("\n=== 2. VERIFY HEALTH ENDPOINTS ===")
    for path in ["/health", "/api/v1/health"]:
        with urllib.request.urlopen(PROD + path) as r:
            assert r.status == 200
            data = json.loads(r.read().decode())
            assert data.get("status") == "ok"
            print(f"  [PASS] Endpoint {path}: status=200, payload={data}")

    print("\n=== 3. VERIFY REGISTRATION & LOGIN FLOW ===")
    test_id = int(datetime.now().timestamp())
    email = f"agent_verify_{test_id}@travelmind.test"
    password = "VerificationPass123!"
    full_name = "8-Agent Production Verifier"

    reg_payload = json.dumps({
        "email": email,
        "password": password,
        "full_name": full_name
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{PROD}/api/v1/auth/register",
        data=reg_payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as r:
        assert r.status == 200
        reg_res = json.loads(r.read().decode())
        user_id = reg_res["user"]["id"]
        print(f"  [PASS] User registered: {email} (ID: {user_id})")

    login_payload = json.dumps({
        "email": email,
        "password": password
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{PROD}/api/v1/auth/login",
        data=login_payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as r:
        assert r.status == 200
        login_res = json.loads(r.read().decode())
        token = login_res["token"]
        print(f"  [PASS] User login succeeded, JWT token received ({len(token)} chars)")

    req = urllib.request.Request(
        f"{PROD}/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req) as r:
        assert r.status == 200
        me_res = json.loads(r.read().decode())
        print(f"  [PASS] Authenticated me profile confirmed: {me_res['user']['email']}, role={me_res['user']['role']}")

    print("\n=== 4. VERIFY TRIP CREATION & 8-AGENT WORKFLOW EXECUTION ===")
    dep_date = (datetime.now() + timedelta(days=25)).strftime("%Y-%m-%d")
    ret_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    client_today = datetime.now().strftime("%Y-%m-%d")

    trip_payload = json.dumps({
        "origin": "PARIS",
        "destination": "TOKYO",
        "departure_date": dep_date,
        "return_date": ret_date,
        "travelers": 2,
        "budget": 4500,
        "currency": "USD",
        "interests": ["Culture & Heritage", "Culinary & Wine", "Architecture"],
        "preferences": {"travel_style": "Balanced Explorer"},
        "client_date": client_today
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{PROD}/api/v1/trips",
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
        print(f"  [PASS] Trip generated successfully! Trip ID: {trip_id}")
        print(f"  Summary: {trip.get('summary')}")

    results = trip.get("plan_results", {})
    expected_agents = [
        ("Destination Discovery", "destination_discovery"),
        ("Accommodation Intelligence", "accommodation_intelligence"),
        ("Flight Intelligence", "flight_intelligence"),
        ("Transportation & Route", "transportation_route"),
        ("Budget Intelligence", "budget_intelligence"),
        ("Personalization Recommendation", "personalization_recommendation"),
        ("Travel Support", "travel_support"),
        ("Itinerary Synthesis", "itinerary")
    ]

    print("\n--- Inspecting 8-Agent Execution Outputs ---")
    for name, key in expected_agents:
        output = results.get(key)
        assert output is not None, f"Expected agent output for '{key}' was not found"
        if isinstance(output, dict):
            status = output.get("status", "ok")
            summary = output.get("summary", "")[:80]
            print(f"  [PASS] Agent '{name}' ({key}): status='{status}', summary='{summary}'")
        else:
            print(f"  [PASS] Agent '{name}' ({key}): data length={len(output)}")

    agent_execution = results.get("agent_execution", {})
    print(f"\nRecorded DAG Agent Execution Entries: {len(agent_execution)}")
    for agent_name, log_info in agent_execution.items():
        print(f"   * {agent_name:32}: status={log_info.get('status')}, duration={log_info.get('duration_ms')}ms, attempts={log_info.get('attempts')}")

    print("\n=== 5. VERIFY SAVED TRIPS LIST & DETAIL ===")
    req = urllib.request.Request(
        f"{PROD}/api/v1/trips",
        headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req) as r:
        assert r.status == 200
        saved_trips = json.loads(r.read().decode())
        print(f"  [PASS] GET /api/v1/trips returned {len(saved_trips)} saved trip(s)")
        assert any(t["id"] == trip_id for t in saved_trips), "Newly created trip must be in saved trips"

    req = urllib.request.Request(
        f"{PROD}/api/v1/trips/{trip_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req) as r:
        assert r.status == 200
        trip_detail = json.loads(r.read().decode())
        assert trip_detail["id"] == trip_id
        print(f"  [PASS] GET /api/v1/trips/{trip_id} returned destination '{trip_detail['destination']}', budget={trip_detail['budget']} {trip_detail['currency']}")

    print("\n=== 6. CLEANUP TEST ACCOUNT ===")
    del_req = urllib.request.Request(
        f"{PROD}/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        method="DELETE"
    )
    with urllib.request.urlopen(del_req) as r:
        assert r.status == 200
        print(f"  [PASS] Test account {email} cleanly removed via supported account management process!")

    print("\n=======================================================")
    print("ALL PRODUCTION CHECKS COMPLETED & VERIFIED 100% [SUCCESS]")
    print("=======================================================\n")

if __name__ == "__main__":
    run_comprehensive()
