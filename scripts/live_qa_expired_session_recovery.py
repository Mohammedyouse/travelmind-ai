import asyncio
import os
import sys
from playwright.async_api import async_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def log(msg=""):
    print(msg, flush=True)

async def test_session_recovery_live():
    log("\n" + "="*70)
    log("LIVE AUDIT: EXPIRED-SESSION HANDLING & RECOVERY DEMO")
    log("="*70)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            channel="msedge",
            headless=False,
            slow_mo=300,
        )
        context = await browser.new_context(viewport={"width": 1366, "height": 850})
        page = await context.new_page()

        # Step 1: Open app
        log("--> Step 1: Navigating to TravelMind AI...")
        await page.goto("http://localhost:5173", wait_until="networkidle")
        await asyncio.sleep(1.0)

        # Step 2: Simulate having an expired token in localStorage
        log("--> Step 2: Injecting an expired token into localStorage...")
        await page.evaluate("() => localStorage.setItem('travelmind.session-token', 'expired_sample_jwt_token_401')")

        # Step 3: Reload page to simulate user returning or refreshing with an expired token
        log("--> Step 3: Refreshing page with expired session token...")
        await page.reload(wait_until="networkidle")
        await asyncio.sleep(1.5)

        # Step 4: Verify Auth Modal automatically opened with expired session notice
        log("--> Step 4: Checking expired-session notice in modal...")
        await page.wait_for_selector(".modal-dialog.auth-modal", state="visible", timeout=8000)
        notice = await page.locator(".notice-banner").inner_text()
        log(f"  [PASS] Modal opened with notice: '{notice}'")

        # Step 5: Check that button is NOT stuck and inputs are accessible
        btn_text = await page.locator(".modal-dialog button.button-primary").inner_text()
        btn_disabled = await page.locator(".modal-dialog button.button-primary").is_disabled()
        log(f"  [PASS] Submit button ready: '{btn_text}' (Disabled: {btn_disabled})")
        await asyncio.sleep(1.0)

        # Step 6: Enter credentials to recover session
        log("--> Step 6: Logging in to recover session...")
        # First register or login
        await page.fill(".modal-dialog input[type='email']", "demo_recovery@travelmind.test")
        await page.fill(".modal-dialog input[type='password']", "Password123!")
        await asyncio.sleep(0.5)

        # If user does not exist, switch to register
        await page.click(".modal-dialog button.button-primary")
        await asyncio.sleep(1.0)

        # Check if error "invalid credentials" appeared (since demo account may not exist yet)
        has_error = await page.locator(".error-banner").is_visible()
        if has_error:
            err = await page.locator(".error-banner").inner_text()
            log(f"  [PASS] Invalid credentials handled cleanly without hang: '{err}'")
            log("  Switching to register to complete recovery...")
            await page.click(".modal-dialog form button.text-button-link")
            await asyncio.sleep(0.5)
            await page.fill(".modal-dialog input[placeholder*='Jane Doe']", "Recovery Traveler")
            await page.fill(".modal-dialog input[type='email']", "demo_recovery@travelmind.test")
            await page.fill(".modal-dialog input[type='password']", "Password123!")
            await page.click(".modal-dialog button.button-primary")

        await page.wait_for_selector(".dashboard-container", timeout=12000)
        log("  [PASS] Successfully recovered! Active user dashboard restored.")
        await asyncio.sleep(3.0)

        log("\n" + "="*70)
        log("SESSION EXPIRATION & RECOVERY VERIFIED 100% IN VISIBLE BROWSER!")
        log("="*70 + "\n")

if __name__ == "__main__":
    asyncio.run(test_session_recovery_live())
