"""
Live Services Verification Script
"""
import urllib.request
import json
import uuid

def main():
    print("=== E2E Integration Check with Live Services ===")
    # 1. Health checks
    for svc, url in [('FastAPI', 'http://localhost:8000/health'), ('n8n', 'http://localhost:5600/healthz')]:
        with urllib.request.urlopen(url) as r:
            body = r.read().decode('utf-8').strip()
            print(f"{svc} health: {r.status} {body}")

    # 2. Register user
    uid = uuid.uuid4().hex[:6]
    reg_req = urllib.request.Request(
        'http://localhost:8000/api/v1/auth/register',
        data=json.dumps({'email': f'usr_{uid}@travelmind.test', 'password': 'Password123!', 'full_name': 'Test User'}).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    with urllib.request.urlopen(reg_req) as r:
        tok = json.loads(r.read().decode('utf-8'))['token']
        print(f"User registered, token received (len={len(tok)})")

    # 3. Plan trip via FastAPI
    plan_req = urllib.request.Request(
        'http://localhost:8000/api/v1/trips/plan',
        data=json.dumps({
            'origin': 'JFK', 'destination': 'CDG',
            'departure_date': '2026-11-01', 'return_date': '2026-11-08',
            'travelers': 2, 'budget': 3500, 'currency': 'USD',
            'interests': ['art', 'food']
        }).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {tok}'},
        method='POST'
    )
    with urllib.request.urlopen(plan_req) as r:
        trip = json.loads(r.read().decode('utf-8'))
        print(f"Trip planned via FastAPI: ID={trip.get('id')} status={trip.get('status')}")

    # 4. Direct call to n8n webhook via Host Port 5600
    n8n_req = urllib.request.Request(
        'http://localhost:5600/webhook/travel-plan-orchestrator',
        data=json.dumps({
            'origin': 'LHR', 'destination': 'FCO',
            'departure_date': '2026-12-10', 'return_date': '2026-12-17',
            'travelers': 1, 'budget': 2000, 'currency': 'EUR'
        }).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'X-N8N-Webhook-Secret': 'travelmind-n8n-secret'},
        method='POST'
    )
    with urllib.request.urlopen(n8n_req) as r:
        n8n_res = json.loads(r.read().decode('utf-8'))
        print(f"n8n Orchestrator Webhook: status={n8n_res.get('status')} tripId={n8n_res.get('tripId')}")

    # 5. Check execution logs in FastAPI
    logs_req = urllib.request.Request('http://localhost:8000/api/v1/n8n/execution-logs')
    with urllib.request.urlopen(logs_req) as r:
        logs = json.loads(r.read().decode('utf-8'))
        print(f"FastAPI audit log recorded {len(logs)} n8n executions.")

    print("=== ALL INTEGRATION CHECKS PASSED SUCCESSFULLY ===")

if __name__ == '__main__':
    main()
