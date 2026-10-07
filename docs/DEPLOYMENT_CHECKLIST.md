# TravelMind AI — Production Deployment Checklist

_Pre-Flight Operational Verification Guide_

---

## 1. Environment & Secret Provisioning

Before deploying to a staging or production environment, ensure all required environment variables are set in `.env`:

- [ ] **Core Secrets**:
  - `SECRET_KEY`: High-entropy 64-character random string (e.g. `openssl rand -hex 32`).
  - `JWT_SECRET_KEY`: Minimum 32-character secret for signing user session tokens.
  - `ENVIRONMENT`: Set to `production`.
  - `APP_ENV`: Set to `production`.
- [ ] **Database Connection**:
  - `DATABASE_URL`: `postgresql://travelmind_user:<strong_password>@postgres:5432/travelmind_prod`
- [ ] **Live AI & Travel Provider API Keys**:
  - `GEMINI_API_KEY`: Active Google Gemini 2.0 Flash API key.
  - `AMADEUS_CLIENT_ID`: Production or test client ID from Amadeus for Developers.
  - `AMADEUS_CLIENT_SECRET`: Client secret from Amadeus.
  - `AMADEUS_BASE_URL`: `https://api.amadeus.com` (production) or `https://test.api.amadeus.com` (testing).
  - `PLACES_API_KEY`: Google Places API key (optional; system automatically uses live OpenStreetMap Nominatim if omitted).
- [ ] **n8n Integration Security**:
  - `N8N_HOST`: `http://n8n:5678` (internal Docker network) or public URL.
  - `N8N_WEBHOOK_URL`: Webhook listener URL for orchestrator callbacks.
  - `N8N_WEBHOOK_SECRET`: High-entropy HMAC secret shared between FastAPI and n8n.
  - `TRAVELMIND_API_BASE_URL`: `http://backend:8000`
- [ ] **Billing & Payment Gateway**:
  - `STRIPE_SECRET_KEY`: Live Stripe API secret key (`sk_live_...`).
  - `STRIPE_WEBHOOK_SECRET`: Stripe endpoint signing secret (`whsec_...`).

---

## 2. Infrastructure & Container Health

- [ ] **Docker Engine**: Docker daemon is active and running.
- [ ] **Docker Compose Up**:
  ```bash
  docker-compose up -d --build
  ```
- [ ] **Container Status Check**:
  ```bash
  docker-compose ps
  ```
  Verify all 5 services report `healthy` or `running`:
  - `travelmind-postgres` (PostgreSQL 16)
  - `travelmind-redis` (Redis 7)
  - `travelmind-backend` (FastAPI)
  - `travelmind-frontend` (Nginx / Vite)
  - `travelmind-n8n` (n8n Automation Engine)

---

## 3. Database Migrations & Integrity

- [ ] **Execute Migrations**:
  ```bash
  docker-compose exec backend alembic upgrade head
  ```
- [ ] **Verify Schema**: Confirm tables exist in PostgreSQL:
  - `users`
  - `trips`
  - `itinerary_items`
  - `conversations`
  - `preferences`
  - `subscriptions`
  - `payments`
  - `notifications`
  - `provider_search_records`
  - `agent_execution_logs`

---

## 4. n8n Workflow Activation

Follow [`docs/N8N_SETUP.md`](file:///c:/Users/USER/OneDrive/Desktop/n8n/travelmind-ai/docs/N8N_SETUP.md) for full instructions:
- [ ] Access n8n at `http://localhost:5600` (or your domain; internal port `5678`).
- [ ] Import all 11 workflows from `n8n/workflows/`.
- [ ] Configure n8n credentials:
  - Header Auth credential with `X-N8N-Webhook-Secret`.
  - Gemini API key.
  - Amadeus OAuth2 client credentials.
  - SMTP or SendGrid mail credentials.
- [ ] Toggle all 11 workflows to **Active**.

---

## 5. End-to-End Verification Pipeline

Execute the end-to-end verification script against the production container:

```bash
docker-compose exec backend python scripts/e2e_smoke_test.py
```

Expected verification milestones:
1. `User Registration & Auth`: Verified (JWT issuance).
2. `Subscription & Quota`: Verified (Tier limits and trip countdown).
3. `Grounded Planning (8 Agents)`: Verified (Live weather, FX, real POIs).
4. `Itinerary Export`: Verified (HTML and JSON formats).
5. `n8n Webhook`: Verified (Secret auth, deduplication, correlation audit).
6. `RBAC Security`: Verified (Traveler 403 Forbidden, Admin 200 OK).

---

## 6. Go-Live Sign-Off

| Verification Milestone | Responsible Role | Status |
|---|---|---|
| Automated Test Suite Passing (56/56) | QA Lead | Completed |
| Frontend Production Build (Zero errors) | Senior Frontend Eng | Completed |
| Non-Destructive DB Safety | Database Architect | Completed |
| API Keys Provisioned | Operations Lead | Required before Go-Live |
| n8n Workflows Active | DevOps Engineer | Required before Go-Live |
