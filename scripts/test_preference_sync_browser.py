import asyncio
import json
import os
import urllib.request
from datetime import datetime
from playwright.async_api import async_playwright


def create_test_user():
    email = f"pref_tester_{int(datetime.now().timestamp())}@travelmind.test"
    password = "Password123!"
    payload = json.dumps({
        "email": email,
        "password": password,
        "full_name": "Preference Tester",
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
    print(f"Created account: {email}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        print("Navigating to http://localhost:5173/ ...")
        await page.goto("http://localhost:5173/", wait_until="networkidle")
        await asyncio.sleep(1)

        # Login
        await page.locator(".navbar-actions button:has-text('Sign In')").click()
        await page.wait_for_selector(".modal-dialog.auth-modal", state="visible")
        await page.fill(".modal-dialog input[type='email']", email)
        await page.fill(".modal-dialog input[type='password']", password)
        await page.locator(".modal-dialog form button.button-primary").click()
        await page.wait_for_selector(".navbar-links button:has-text('Trip Planner')", timeout=15000)
        print("Logged in successfully.")

        # Go to Preferences via Settings icon button
        await page.locator("button[title='Settings']").click()
        await page.wait_for_selector(".preferences-view", state="visible")
        print("Navigated to Preferences.")

        # Select EUR currency and Save
        currency_select = page.locator(".preferences-view select").nth(1)
        await currency_select.select_option("EUR")
        await page.locator(".preferences-view button[type='submit']").click()
        await page.wait_for_selector(".preferences-view .success-banner", state="visible")
        print("Preferences saved with EUR currency.")

        # Navigate to Trip Planner Wizard
        await page.locator(".navbar-links button:has-text('Trip Planner')").click()
        await page.wait_for_selector(".wizard-card", state="visible")
        print("Navigated to Trip Planner Wizard.")

        # Step 1: fill origin and destination
        await page.fill(".wizard-step-content input", "Paris")
        await page.locator(".wizard-step-content input").nth(1).fill("Rome")
        await page.locator(".wizard-actions-bar button.button-primary").click()
        print("Completed Step 1.")

        # Step 2: fill dates
        today_val = datetime.now().strftime("%Y-%m-%d")
        # Find date inputs
        date_inputs = page.locator(".wizard-step-content input[type='date']")
        await date_inputs.first.fill(today_val)
        await page.locator(".wizard-actions-bar button.button-primary").click()
        print("Completed Step 2.")

        # Step 3: Check preferred currency
        await page.wait_for_selector(".wizard-step-content select", state="visible")
        curr_val = await page.locator(".wizard-step-content select").input_value()
        print(f"Wizard Step 3 selected currency: '{curr_val}'")
        assert curr_val == "EUR", f"Expected EUR but got {curr_val}"
        print("SUCCESS! User preferred currency EUR synchronized perfectly to Trip Wizard!")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(run())
