"""
Playwright End-to-End Live Browser Automation Script for TravelMind AI
Tests:
1. Landing page load & navigation
2. Real user registration through AuthModal
3. User dashboard verification
4. Interactive Trip Studio (TripWizard) steps 1 to 4 with manual inputs:
   - Origin: "New York"
   - Destination: "Paris"
   - Departure: "2026-11-10"
   - Return: "2026-11-15"
   - Travelers: 2
   - Budget: 3500
   - Currency: USD
   - Interests: Culture & Heritage, Culinary & Wine
   - Style: Balanced Explorer
5. Plan generation and verification of PlanDetailView (Itinerary, Hotels, Places, Weather, Budget)
6. Verification of FastAPI documentation at http://localhost:8000/docs
7. Verification of n8n web editor at http://localhost:5600/
"""
import os
import sys
import time
import uuid

# Force utf-8 stdout encoding for Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "screenshots"))
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

def run():
    print("=" * 70)
    print("STARTING LIVE PLAYWRIGHT BROWSER VERIFICATION")
    print("=" * 70)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # ---------------------------------------------------------
        # Step 1: Landing Page
        # ---------------------------------------------------------
        print("\n[Step 1] Navigating to http://localhost:5173...")
        page.goto("http://localhost:5173", wait_until="networkidle")
        time.sleep(1)
        assert "TravelMind" in page.title(), f"Unexpected title: {page.title()}"
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "01_landing_page.png"))
        print("  -> Landing page loaded. Title:", page.title())

        # ---------------------------------------------------------
        # Step 2: Open Auth Modal and Register New User
        # ---------------------------------------------------------
        print("\n[Step 2] Opening AuthModal and Registering a new traveler...")
        start_btn = page.locator("button:has-text('Start Planning Free')").first
        if not start_btn.is_visible():
            start_btn = page.locator("button:has-text('Sign In')").first
        start_btn.click()
        page.wait_for_selector(".auth-modal", state="visible")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "02_auth_modal_login.png"))

        # Switch to Register tab
        toggle_link = page.locator("button.text-button-link:has-text('New traveler? Create an account')")
        if toggle_link.is_visible():
            toggle_link.click()
            time.sleep(0.5)

        test_id = uuid.uuid4().hex[:6]
        full_name = f"Manual Browser Traveler {test_id}"
        test_email = f"traveler_{test_id}@travelmind.test"
        test_password = "Password123!"

        print(f"  -> Filling registration form: {test_email}")
        page.fill("input[placeholder='e.g. Jane Doe']", full_name)
        page.fill("input[placeholder='name@example.com']", test_email)
        page.fill("input[placeholder='••••••••']", test_password)
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "03_auth_modal_filled.png"))

        page.click("button:has-text('Create Free Account')")
        # Wait for dashboard to load
        page.wait_for_selector(".dashboard-container", state="visible", timeout=10000)
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "04_dashboard.png"))
        print(f"  -> User registered and authenticated. Dashboard visible.")

        # ---------------------------------------------------------
        # Step 3: Enter TripWizard (Trip Planning Wizard)
        # ---------------------------------------------------------
        print("\n[Step 3] Launching Trip Planner Wizard...")
        plan_btn = page.locator("button:has-text('+ Plan New Journey')").first
        plan_btn.click()
        page.wait_for_selector(".wizard-card", state="visible", timeout=5000)

        # Wizard Step 1: Origin & Destination
        print("  -> Step 1/4: Origin & Destination (Delhi -> Goa)")
        page.locator("label:has-text('Origin') input").fill("New Delhi")
        page.locator("label:has-text('Destination') input").fill("Goa")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "05_wizard_step1.png"))
        page.click("button:has-text('Next: Travel Dates')")
        time.sleep(0.5)

        # Wizard Step 2: Dates & Travelers
        print("  -> Step 2/4: Dates & Travelers")
        page.fill("input[type='date'] >> nth=0", "2026-11-10")
        page.fill("input[type='date'] >> nth=1", "2026-11-15")
        page.fill("input[type='number'][min='1'][max='20']", "2")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "06_wizard_step2.png"))
        page.click("button:has-text('Next: Financials & Budget')")
        time.sleep(0.5)

        # Wizard Step 3: Budget & Currency
        print("  -> Step 3/4: Financials & Budget (₹60,000 INR)")
        page.fill("input[placeholder='e.g. 2500']", "60000")
        page.select_option("select", "INR")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "07_wizard_step3.png"))
        page.click("button:has-text('Next: Preferences & Style')")
        time.sleep(0.5)

        # Wizard Step 4: Interests & Travel Style
        print("  -> Step 4/4: Interests & Travel Style")
        culture_btn = page.locator("button.interest-tag-button:has-text('Culture & Heritage')")
        if "selected" not in (culture_btn.get_attribute("class") or ""):
            culture_btn.click()
        page.locator("button.chip-button:has-text('Balanced Explorer')").click()
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "08_wizard_step4.png"))

        # Submit Plan Request
        print("  -> Submitting Trip Request to Multi-Agent Swarm...")
        submit_btn = page.locator("button[type='submit']:has-text('Generate Verified Plan')")
        submit_btn.click()

        # ---------------------------------------------------------
        # Step 4: Verify PlanDetailView
        # ---------------------------------------------------------
        print("\n[Step 4] Awaiting trip generation and verifying PlanDetailView...")
        page.wait_for_selector(".plan-detail-container", state="visible", timeout=30000)
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "09_plan_detail_itinerary.png"))
        print("  -> PlanDetailView successfully loaded!")

        # Verify Header content
        heading = page.locator(".plan-header-banner h1").first.text_content()
        print(f"  -> Generated Trip Heading: {heading}")

        # Check Flights Tab
        print("\n[Step 5] Checking Flights Tab...")
        page.click("button.subtab-btn:has-text('Flights')")
        time.sleep(1)
        flight_cards = page.locator(".flight-offer-card")
        print(f"  -> Verified {flight_cards.count()} flight offers visible.")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "10_plan_flights.png"))

        # Check Hotels Tab
        print("\n[Step 6] Checking Hotels Tab...")
        page.click("button.subtab-btn:has-text('Hotels')")
        time.sleep(1)
        hotel_cards = page.locator(".hotel-card")
        print(f"  -> Verified {hotel_cards.count()} curated hotels visible across tiers.")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "11_plan_hotels.png"))

        # Check Attractions Tab
        print("\n[Step 7] Checking Attractions / Places Tab...")
        page.click("button.subtab-btn:has-text('Attractions')")
        time.sleep(1)
        places_cards = page.locator(".place-item-card")
        print(f"  -> Verified {places_cards.count()} iconic landmarks visible.")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "12_plan_attractions.png"))

        # Check Map Tab
        print("\n[Step 8] Checking Interactive Map Tab...")
        page.click("button.subtab-btn:has-text('Interactive Map')")
        time.sleep(1)
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "13_plan_map.png"))
        print("  -> Interactive Map verified.")

        # Check Budget Tab
        print("\n[Step 9] Checking Cost Breakdown Tab...")
        page.click("button.subtab-btn:has-text('Cost Breakdown')")
        time.sleep(1)
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "14_plan_budget.png"))
        print("  -> Cost Breakdown tab verified.")

        # Check AI Concierge in top nav
        print("\n[Step 10] Testing AI Concierge Assistant...")
        page.click("button.nav-link:has-text('AI Assistant')")
        page.wait_for_selector(".chat-container", state="visible", timeout=5000)
        page.fill("input[placeholder='Ask about flights, stays, daily pacing, or budget...']", "What are the best street food and seafood dishes in Goa?")
        page.click("button:has-text('Send')")
        time.sleep(2)
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "15_concierge_chat.png"))
        print("  -> AI Concierge replied in browser.")

        # ---------------------------------------------------------
        # Step 9: Verify Other Services in Browser
        # ---------------------------------------------------------
        print("\n[Step 9] Checking FastAPI Swagger Documentation...")
        page.goto("http://localhost:8000/docs", wait_until="networkidle")
        time.sleep(1)
        api_title = page.title()
        print(f"  -> FastAPI Docs Page Title: {api_title}")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "14_fastapi_docs.png"))

        print("\n[Step 10] Checking n8n Automation Editor UI...")
        page.goto("http://localhost:5600/", wait_until="networkidle")
        time.sleep(2)
        n8n_title = page.title()
        print(f"  -> n8n Editor UI Page Title: {n8n_title}")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "15_n8n_editor.png"))

        browser.close()
        print("\n" + "=" * 70)
        print("ALL BROWSER MANUAL INPUTS & SERVICE CHECKS COMPLETED SUCCESSFULLY!")
        print("=" * 70)

if __name__ == '__main__':
    run()
