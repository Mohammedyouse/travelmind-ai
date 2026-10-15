import asyncio
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def create_test_user():
    email = f"dubai_tester_{int(datetime.now().timestamp())}@travelmind.test"
    password = "Password123!"
    payload = json.dumps({
        "email": email,
        "password": password,
        "full_name": "Dubai Destination Tester",
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
    email, password, token = create_test_user()
    print(f"[TEST USER] Created: {email}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=False, slow_mo=150)
        context = await browser.new_context(viewport={"width": 1366, "height": 850})
        page = await context.new_page()

        console_errors = []
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)

        print("[NAVIGATE] Opening http://localhost:5173/ ...")
        await page.goto("http://localhost:5173/", wait_until="networkidle")
        await asyncio.sleep(1)

        # Login
        print("[AUTH] Signing in...")
        await page.locator(".navbar-actions button:has-text('Sign In')").click()
        await page.wait_for_selector(".modal-dialog.auth-modal", state="visible")
        await page.fill(".modal-dialog input[type='email']", email)
        await page.fill(".modal-dialog input[type='password']", password)
        await page.locator(".modal-dialog form button.button-primary").click()
        await page.wait_for_selector(".navbar-links button:has-text('Trip Planner')", timeout=15000)
        print("[AUTH] Successfully logged in.")

        # Go to Trip Planner
        await page.locator(".navbar-links button:has-text('Trip Planner')").click()
        await page.wait_for_selector(".wizard-card", state="visible")
        print("[WIZARD] Step 1: Destination Selection")

        # Fill Origin
        await page.fill(".wizard-step-content input", "London")

        # Click the 'Dubai' popular destination pill
        dubai_pill = page.locator(".suggestion-chips button.chip-button:has-text('Dubai')")
        await dubai_pill.click()
        dest_val = await page.locator(".wizard-step-content input").nth(1).input_value()
        print(f"[WIZARD] Destination set via pill: '{dest_val}'", flush=True)
        assert "Dubai" in dest_val, f"Expected Dubai but got {dest_val}"

        # Advance to Step 2
        await page.locator(".wizard-actions-bar button.button-primary").click()
        await page.wait_for_selector(".wizard-step-content input[type='date']", state="visible")
        print("[WIZARD] Step 2: Date Configuration")

        today = datetime.now()
        dep_date = (today + timedelta(days=20)).strftime("%Y-%m-%d")
        ret_date = (today + timedelta(days=25)).strftime("%Y-%m-%d")
        date_inputs = page.locator(".wizard-step-content input[type='date']")
        await date_inputs.first.fill(dep_date)
        await date_inputs.nth(1).fill(ret_date)

        # Advance to Step 3
        await page.locator(".wizard-actions-bar button.button-primary").click()
        await page.wait_for_selector(".wizard-step-content select", state="visible")
        print("[WIZARD] Step 3: Budget Configuration")

        # Advance to Step 4
        await page.locator(".wizard-actions-bar button.button-primary").click()
        await page.wait_for_selector(".wizard-step-content h3:has-text('4. Personalize Your Experiences')", state="visible")
        print("[WIZARD] Step 4: Personalize & Generate", flush=True)

        # Click Generate Plan
        gen_btn = page.locator(".wizard-actions-bar button[type='submit']")
        await gen_btn.click()
        print("[PIPELINE] 8-Agent pipeline executing for Dubai trip...", flush=True)

        # Wait for PlanDetailView to load
        await page.wait_for_selector(".plan-header-banner", timeout=40000)
        print("[DETAIL VIEW] Plan loaded successfully!", flush=True)

        # Check Tab: Accommodations / Stays
        print("[VERIFY] Checking Stays tab...", flush=True)
        await page.locator(".plan-tabs-bar button:has-text('Hotels & Stays')").click()
        await page.wait_for_selector(".hotel-cards-grid", state="visible")

        hotel_cards = page.locator(".hotel-cards-grid .hotel-card")
        hotel_count = await hotel_cards.count()
        print(f"[VERIFY] Dubai Hotels Count: {hotel_count}", flush=True)
        assert hotel_count >= 5, f"Expected at least 5 hotels for Dubai, found {hotel_count}"

        hotel_text = await page.locator(".hotel-cards-grid").inner_text()
        print(f"[VERIFY] Sample hotels in view: {hotel_text[:160]}...", flush=True)
        assert any(k in hotel_text for k in ("Rove", "Atlantis", "Taj", "Burj Al Arab")), "Expected verified Dubai iconic hotels in directory"

        # Check Tab: Attractions / Landmarks
        print("[VERIFY] Checking Attractions tab...", flush=True)
        await page.locator(".plan-tabs-bar button:has-text('Attractions')").click()
        await page.wait_for_selector(".places-grid", state="visible")

        place_cards = page.locator(".places-grid .place-item-card")
        place_count = await place_cards.count()
        print(f"[VERIFY] Dubai Landmarks Count: {place_count}", flush=True)
        assert place_count >= 6, f"Expected at least 6 landmarks for Dubai, found {place_count}"

        places_text = await page.locator(".places-grid").inner_text()
        print(f"[VERIFY] Sample attractions in view: {places_text[:160]}...", flush=True)
        assert any(k in places_text for k in ("Burj Khalifa", "Dubai Mall", "Museum of the Future")), "Expected verified Dubai landmarks"

        # Check Console Errors
        print(f"[CONSOLE] Captured errors count: {len(console_errors)}", flush=True)
        assert len(console_errors) == 0, f"Unexpected console errors: {console_errors}"

        # Take screenshot for proof
        await page.screenshot(path="screenshots/dubai_verified_directory.png")
        print("[SCREENSHOT] Saved to screenshots/dubai_verified_directory.png", flush=True)

        print("\n=======================================================", flush=True)
        print("PASS: Dubai Verified Directory E2E Browser Test Verified!", flush=True)
        print("=======================================================\n", flush=True)

        await asyncio.sleep(2)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(run())
