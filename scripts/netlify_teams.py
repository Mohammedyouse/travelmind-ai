"""Check which Netlify team/account can create a new site."""
import httpx

TOKEN = "nfc_5BsXNTKXQSePPnNTZUd1ovV5RKwDCA8ka355"
BASE  = "https://api.netlify.com/api/v1"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

# List teams
r = httpx.get(f"{BASE}/accounts", headers=HEADERS, timeout=15)
print("Teams:", r.status_code)
if r.status_code == 200:
    for acc in r.json():
        print(f"  slug={acc.get('slug')} name={acc.get('name')} type={acc.get('type_name')} sites_limit={acc.get('sites_count','?')}/{acc.get('capabilities',{}).get('sites','?')}")
        print(f"    id={acc.get('id')} plan={acc.get('billing_plan','?')}")
