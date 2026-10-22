"""
Full Netlify deployment script for TravelMind AI.
Creates site, sets env vars, deploys dist/ via ZIP upload.
"""
import os, sys, json, zipfile, io, pathlib, httpx, time

TOKEN = "nfc_5BsXNTKXQSePPnNTZUd1ovV5RKwDCA8ka355"
BASE  = "https://api.netlify.com/api/v1"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
DIST_DIR = pathlib.Path("frontend/dist")

# Backend URL — will be updated after Render deploy
BACKEND_URL = "https://travelmind-api.onrender.com"

def api(method, path, **kw):
    r = httpx.request(method, f"{BASE}{path}", headers=HEADERS, timeout=30, **kw)
    if r.status_code >= 400:
        print(f"  ERROR {r.status_code}: {r.text[:300]}")
        return None
    return r.json() if r.text else {}

# ── 1. Check for existing TravelMind site ────────────────────────────────────
print("\n[1] Listing existing sites...")
sites = api("GET", "/sites?per_page=100") or []
tm_site = next((s for s in sites if "travelmind" in s.get("name","").lower()), None)

if tm_site:
    site_id   = tm_site["id"]
    site_name = tm_site["name"]
    site_url  = tm_site.get("ssl_url") or tm_site.get("url")
    print(f"    Found existing site: {site_name} ({site_url})")
else:
    # ── 2. Create new site ────────────────────────────────────────────────────
    print("\n[2] Creating new Netlify site...")
    payload = {"name": "travelmind-ai"}
    result  = api("POST", "/sites?account_slug=mohammed-lubam7q", json=payload)
    if not result:
        print("    Trying fallback account slug...")
        result = api("POST", "/sites", json=payload)
    if not result:
        sys.exit("Could not create site")
    site_id   = result["id"]
    site_name = result["name"]
    site_url  = result.get("ssl_url") or result.get("url")
    print(f"    Created: {site_name} -> {site_url}")

print(f"\n    Site ID : {site_id}")
print(f"    Site URL: {site_url}")

# ── 3. Set environment variables ──────────────────────────────────────────────
print("\n[3] Setting environment variables...")
env_payload = {
    "env": {
        "VITE_API_BASE_URL": {"scopes": ["builds", "runtime"], "values": [{"value": BACKEND_URL, "context": "production"}]},
        "NODE_VERSION":      {"scopes": ["builds"], "values": [{"value": "20", "context": "all"}]},
    }
}
env_result = api("PATCH", f"/sites/{site_id}", json=env_payload)
if env_result is not None:
    print(f"    Env vars set (VITE_API_BASE_URL={BACKEND_URL})")
else:
    print("    Env var setting via PATCH failed; trying env_vars endpoint...")
    for key, val in [("VITE_API_BASE_URL", BACKEND_URL), ("NODE_VERSION", "20")]:
        r = api("PUT", f"/sites/{site_id}/env/{key}", json={"key": key, "scopes": ["builds","runtime"], "values": [{"value": val, "context": "all"}]})
        print(f"    {key}: {'ok' if r is not None else 'FAIL'}")

# ── 4. Create ZIP of dist/ ────────────────────────────────────────────────────
print("\n[4] Zipping dist/ directory...")
zip_buf = io.BytesIO()
with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
    for f in DIST_DIR.rglob("*"):
        if f.is_file():
            arcname = f.relative_to(DIST_DIR)
            zf.write(f, arcname)
zip_buf.seek(0)
zip_bytes = zip_buf.read()
print(f"    ZIP size: {len(zip_bytes):,} bytes")

# ── 5. Deploy via ZIP upload ──────────────────────────────────────────────────
print("\n[5] Uploading deployment...")
deploy_headers = {**HEADERS, "Content-Type": "application/zip"}
r = httpx.post(
    f"{BASE}/sites/{site_id}/deploys",
    headers=deploy_headers,
    content=zip_bytes,
    timeout=120,
)
if r.status_code >= 400:
    print(f"    UPLOAD ERROR {r.status_code}: {r.text[:400]}")
    sys.exit(1)
deploy = r.json()
deploy_id  = deploy.get("id")
deploy_url = deploy.get("deploy_ssl_url") or deploy.get("deploy_url") or site_url
print(f"    Deploy ID : {deploy_id}")
print(f"    Deploy URL: {deploy_url}")

# ── 6. Poll until ready ───────────────────────────────────────────────────────
print("\n[6] Waiting for deploy to go live...")
for i in range(30):
    time.sleep(5)
    d = api("GET", f"/deploys/{deploy_id}") or {}
    state = d.get("state", "unknown")
    print(f"    [{i*5}s] state={state}")
    if state in ("ready", "current"):
        print(f"\n    LIVE at: {deploy_url}")
        break
    if state == "error":
        print(f"    Deploy FAILED: {d.get('error_message')}")
        sys.exit(1)

# ── 7. Print final summary ────────────────────────────────────────────────────
print("\n" + "="*60)
print("NETLIFY DEPLOY COMPLETE")
print(f"  Site name : {site_name}")
print(f"  Site URL  : {site_url}")
print(f"  Deploy URL: {deploy_url}")
print(f"  Backend   : {BACKEND_URL}")
print("="*60)
