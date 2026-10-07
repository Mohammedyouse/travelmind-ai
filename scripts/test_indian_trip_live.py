import urllib.request
import json
import sys
import uuid

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://localhost:8000"

def run_test():
    print("=== Testing TravelMind AI End-to-End Live Services ===")

    # 1. Register test user
    uid = uuid.uuid4().hex[:6]
    reg_req = urllib.request.Request(
        f"{BASE_URL}/api/v1/auth/register",
        data=json.dumps({"email": f"tester_{uid}@travelmind.test", "password": "Password123!", "full_name": "Test Traveler"}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(reg_req) as resp:
        reg_res = json.loads(resp.read().decode())
        token = reg_res["token"]
        print(f"[OK] Registered user 'tester_{uid}'. Token prefix: {token[:12]}...")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    # 2. Create Indian Trip: Delhi -> Goa in INR
    trip_payload = {
        "origin": "NEW DELHI",
        "destination": "GOA",
        "departure_date": "2026-11-10",
        "return_date": "2026-11-15",
        "travelers": 2,
        "budget": 60000,
        "currency": "INR",
        "interests": ["beaches", "seafood", "heritage", "culture"],
        "preferences": {
            "travel_style": "Balanced Explorer"
        }
    }
    print(f"\n[INFO] Creating Trip: Delhi -> Goa (INR 60,000, 2 Travelers)...")
    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/trips/plan",
        data=json.dumps(trip_payload).encode(),
        headers=headers,
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        trip = json.loads(resp.read().decode())
        trip_id = trip["id"]
        print(f"[OK] Trip created successfully! ID: {trip_id}")

    results = trip.get("plan_results") or {}

    # Inspect Flights
    flight_data = results.get("flight_intelligence", {}).get("data", {})
    flight_offers = flight_data.get("offers", [])
    print(f"\n--- FLIGHT INTELLIGENCE ({len(flight_offers)} offers found) ---")
    for idx, f in enumerate(flight_offers):
        print(f"  [{idx+1}] {f.get('carrier_names', ['Airline'])[0]} {f.get('flight_number', '')} | {f.get('cabin_class', 'Economy')} | {f.get('price')} {f.get('currency')} | Stops: {f.get('stops')} | Baggage: {f.get('baggage', 'N/A')}")
    assert len(flight_offers) >= 3, f"Expected at least 3 flight offers, got {len(flight_offers)}"

    # Inspect Hotels
    hotel_data = results.get("accommodation_intelligence", {}).get("data", {})
    hotels = hotel_data.get("hotels", [])
    print(f"\n--- ACCOMMODATION INTELLIGENCE ({len(hotels)} properties found) ---")
    for idx, h in enumerate(hotels):
        print(f"  [{idx+1}] {h.get('name')} | Tier: {h.get('tier')} | Rating: {h.get('rating')}* | INR {h.get('price_per_night')}/night | Area: {h.get('neighborhood')}")
    assert len(hotels) >= 4, f"Expected at least 4 hotels across tiers, got {len(hotels)}"

    # Inspect Attractions
    dest_data = results.get("destination_discovery", {}).get("data", {})
    places = dest_data.get("places", [])
    coords = dest_data.get("coordinates", {})
    print(f"\n--- DESTINATION DISCOVERY ({len(places)} iconic landmarks found) ---")
    print(f"  Destination Coordinates: lat={coords.get('latitude')}, lon={coords.get('longitude')}")
    for idx, p in enumerate(places[:8]):
        print(f"  [{idx+1}] {p.get('name')} ({p.get('category')}) - {p.get('address')} | GPS: {p.get('latitude')}, {p.get('longitude')}")
    if len(places) > 8:
        print(f"  ... and {len(places) - 8} more places.")
    assert len(places) >= 10, f"Expected at least 10 iconic attractions, got {len(places)}"
    assert coords.get("latitude") and coords.get("latitude") > 14 and coords.get("latitude") < 16, f"Invalid Goa latitude: {coords.get('latitude')}"

    # Inspect Itinerary
    itinerary = results.get("itinerary", {})
    days = itinerary.get("days", [])
    print(f"\n--- DAILY ITINERARY ({len(days)} days) ---")
    for d in days:
        print(f"  Day {d.get('day')}: {d.get('title')}")
        print(f"    * Morning: {d.get('morning', {}).get('activity')} ({d.get('morning', {}).get('cost', '')})")
        print(f"    * Afternoon: {d.get('afternoon', {}).get('activity')} ({d.get('afternoon', {}).get('cost', '')})")
        print(f"    * Evening: {d.get('evening', {}).get('activity')} ({d.get('evening', {}).get('cost', '')})")
        print(f"    * Dining Tip: {d.get('dining_recommendation', 'N/A')}")
        print(f"    * Transit Tip: {d.get('transit_tip', 'N/A')}")

    # Inspect Budget
    budget_data = results.get("budget_intelligence", {}).get("data", {})
    print(f"\n--- BUDGET INTELLIGENCE ---")
    print(f"  Total Estimated: INR {budget_data.get('total')} {budget_data.get('currency')}")
    print(f"  Contingency: INR {budget_data.get('contingency')}")
    print(f"  Remaining: INR {budget_data.get('remaining')}")
    print(f"  Items: {budget_data.get('items')}")

    # 3. Test AI Assistant Chat
    print(f"\n--- TESTING AI CONCIERGE CHAT ---")
    chat_queries = [
        "What are the best street food and seafood dishes I must eat in Goa?",
        "What should I pack for this trip given Goa's climate?",
        "Can you suggest luxury heritage stays vs backpacker hostels in Goa?"
    ]
    for q in chat_queries:
        chat_req = urllib.request.Request(
            f"{BASE_URL}/api/v1/conversations",
            data=json.dumps({"content": q, "trip_id": trip_id}).encode(),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(chat_req) as resp:
            chat_res = json.loads(resp.read().decode())
            print(f"\n[User Question]: {q}")
            print(f"[Concierge Answer]:\n{chat_res.get('content')}\n")
            assert len(chat_res.get("content", "")) > 50, "Concierge reply is too short!"

    print("\n[SUCCESS] ALL VERIFICATIONS PASSED! System produces rich, accurate, multi-tiered Indian travel intelligence.")

if __name__ == "__main__":
    run_test()
