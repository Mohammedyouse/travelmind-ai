import asyncio
import json
import urllib.request
from datetime import datetime
from playwright.async_api import async_playwright

def register_user():
    email = f"user_{int(datetime.now().timestamp())}@travelmind.test"
    password = "Password123!"
    payload = json.dumps({
        "email": email,
        "password": password,
        "full_name": "Test User",
    }).encode("utf-8")
    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/v1/auth/register",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        return email, password

async def inspect():
    email, password = register_user()
    print("Registered user:", email)
    
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="msedge", headless=True)
        page = await b.new_page()
        page.on("console", lambda msg: print("CONSOLE:", msg.text))
        page.on("request", lambda req: print("REQUEST:", req.method, req.url))
        
        await page.goto("http://127.0.0.1:5173/")
        await asyncio.sleep(1)
        
        print("Clicking Sign In...")
        await page.click(".navbar-actions button:has-text('Sign In')")
        await page.wait_for_selector(".modal-dialog")
        
        await page.fill(".modal-dialog input[type='email']", email)
        await page.fill(".modal-dialog input[type='password']", password)
        
        print("Submitting login form...")
        await page.click(".modal-dialog form button.button-primary")
        await asyncio.sleep(3)
        
        modal_visible = await page.locator(".modal-dialog").is_visible()
        print("Modal still visible?", modal_visible)
        
        planner_visible = await page.locator(".navbar-links button:has-text('Trip Planner')").is_visible()
        print("Trip Planner button visible in navbar?", planner_visible)
        
        await b.close()

if __name__ == "__main__":
    asyncio.run(inspect())
