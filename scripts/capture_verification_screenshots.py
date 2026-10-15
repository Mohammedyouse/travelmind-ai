import asyncio
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone
from playwright.async_api import async_playwright


def create_test_user():
    email = f"mohammed_{int(datetime.now().timestamp())}@travelmind.test"
    password = "Password123!"
    payload = json.dumps({
        "email": email,
        "password": password,
        "full_name": "Mohammed",
    }).encode("utf-8")

    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/v1/auth/register",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return email, password, data["token"]


async def run():
    os.makedirs("screenshots", exist_ok=True)
    email, password, token = create_test_user()
    print(f"Created traveler account: {email}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        print("Navigating to http://127.0.0.1:5173/ ...")
        await page.goto("http://127.0.0.1:5173/", wait_until="networkidle")
        await asyncio.sleep(1)

        # 1. Sign In via UI Modal
        print("Clicking Sign In button...")
        await page.locator(".navbar-actions button:has-text('Sign In')").click()
        await page.wait_for_selector(".modal-dialog.auth-modal", state="visible")
        await asyncio.sleep(0.5)

        print("Filling credentials...")
        await page.fill(".modal-dialog input[type='email']", email)
        await page.fill(".modal-dialog input[type='password']", password)
        await asyncio.sleep(0.3)

        print("Submitting login form...")
        await page.locator(".modal-dialog form button.button-primary").click()
        
        # Wait for dashboard navigation
        print("Waiting for dashboard...")
        await page.wait_for_selector(".navbar-links button:has-text('Trip Planner')", timeout=15000)
        await asyncio.sleep(1)

        # Capture Dashboard
        await page.screenshot(path="screenshots/00_user_dashboard.png")

        # 2. Open Trip Planner Wizard
        print("Opening Trip Planner Wizard...")
        await page.locator(".navbar-links button:has-text('Trip Planner')").click()
        await page.wait_for_selector(".wizard-card", timeout=10000)
        await asyncio.sleep(0.8)

        # Step 1: Origin & Destination
        print("Filling Step 1 (Origin & Destination)...")
        await page.fill("input[placeholder*='Delhi']", "DELHI")
        await page.fill("input[placeholder*='Goa']", "MUMBAI")
        await page.locator("button:has-text('Next: Travel Dates')").click()
        await asyncio.sleep(0.5)

        # Step 2: Date Validation Check
        print("Testing Step 2 date validation: Attempting yesterday's departure date...")
        today = datetime.now(timezone.utc).date()
        yesterday = today - timedelta(days=1)
        departure_input = page.locator("label:has-text('Departure Date') input[type='date']")
        
        await departure_input.fill(yesterday.isoformat())
        await page.keyboard.press("Tab")
        await asyncio.sleep(0.8)

        # Capture 01: Date validation warning banner
        print("Capturing screenshots/01_trip_planner_date_validation.png ...")
        await page.screenshot(path="screenshots/01_trip_planner_date_validation.png")

        # Now set valid future dates: tomorrow to +5 days
        tomorrow = today + timedelta(days=1)
        return_date = today + timedelta(days=6)
        print(f"Setting valid dates: {tomorrow.isoformat()} to {return_date.isoformat()}...")
        await departure_input.fill(tomorrow.isoformat())
        return_input = page.locator("label:has-text('Return Date') input[type='date']")
        await return_input.fill(return_date.isoformat())
        await asyncio.sleep(0.5)

        # Step 3: Budget
        await page.locator("button:has-text('Next: Financials & Budget')").click()
        await asyncio.sleep(0.5)

        # Step 4: Preferences & Submit
        await page.locator("button:has-text('Next: Preferences & Style')").click()
        await asyncio.sleep(0.5)

        print("Submitting trip plan for autonomous 8-agent pipeline execution...")
        await page.locator("button:has-text('Generate Verified Plan')").click()

        # Wait for PlanDetailView to load
        print("Waiting for agent DAG execution to finish...")
        await page.wait_for_selector(".plan-detail-container", timeout=40000)
        await asyncio.sleep(1.5)

        # Capture 02: Daily Schedule
        print("Capturing screenshots/02_daily_schedule.png ...")
        await page.screenshot(path="screenshots/02_daily_schedule.png")

        # Capture 03: Flights Tab
        print("Capturing screenshots/03_flights.png ...")
        await page.click("button:has-text('Flights')")
        await asyncio.sleep(0.8)
        await page.screenshot(path="screenshots/03_flights.png")

        # Capture 04: Hotels Tab
        print("Capturing screenshots/04_hotels.png ...")
        await page.click("button:has-text('Hotels & Stays')")
        await asyncio.sleep(0.8)
        await page.screenshot(path="screenshots/04_hotels.png")

        # Capture 05: Attractions Tab
        print("Capturing screenshots/05_attractions.png ...")
        await page.click("button:has-text('Attractions')")
        await asyncio.sleep(0.8)
        await page.screenshot(path="screenshots/05_attractions.png")

        # Capture 06: Interactive Map (Leaflet OpenStreetMap)
        print("Capturing screenshots/06_interactive_map.png ...")
        await page.click("button:has-text('Interactive Map')")
        await asyncio.sleep(2.5)  # Let OSM tiles and marker pins render
        await page.screenshot(path="screenshots/06_interactive_map.png")

        # Capture 07: Budget Breakdown
        print("Capturing screenshots/07_budget_breakdown.png ...")
        await page.click("button:has-text('Cost Breakdown')")
        await asyncio.sleep(0.8)
        await page.screenshot(path="screenshots/07_budget_breakdown.png")

        # Capture 08: Weather & Checklist
        print("Capturing screenshots/08_weather_checklist.png ...")
        await page.click("button:has-text('Weather & Checklist')")
        await asyncio.sleep(0.8)
        await page.screenshot(path="screenshots/08_weather_checklist.png")

        # Capture 09: Light Mode (Theme Toggle)
        print("Capturing screenshots/09_light_mode.png ...")
        theme_toggle = page.locator(".theme-toggle-btn")
        await theme_toggle.click()
        await asyncio.sleep(1.0)
        await page.screenshot(path="screenshots/09_light_mode.png")

        # Capture 10: Dark Mode
        print("Capturing screenshots/10_dark_mode.png ...")
        await theme_toggle.click()
        await asyncio.sleep(1.0)
        await page.screenshot(path="screenshots/10_dark_mode.png")

        print("All verification screenshots successfully captured!")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(run())
