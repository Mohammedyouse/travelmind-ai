# n8n Workflow Automation & Integration Guide

_TravelMind AI — Production Operational Setup_

---

## 1. Overview

**n8n** is a core operational workflow automation engine in TravelMind AI. While FastAPI orchestrates low-latency internal agents and transactional database logic, n8n handles:
- Cross-service event workflows (e.g. notifications, itinerary delivery).
- Scheduled travel reminders and background polling.
- WhatsApp / omni-channel conversational messaging integration.
- Distributed fallback orchestration and error alerting.

FastAPI and n8n communicate bidirectionally using secure HTTP webhooks with HMAC/token authentication (`X-N8N-Webhook-Secret`), request deduplication, correlation IDs, and execution audit logging.

---

## 2. Directory Structure & The 11 Production Workflows

All production workflows are located in the repository under [`n8n/workflows/`](file:///c:/Users/USER/OneDrive/Desktop/n8n/travelmind-ai/n8n/workflows/):

| # | Workflow File | Primary Trigger | Core Responsibilities |
|---|---|---|---|
| **01** | `01-main-travel-planning-orchestrator.json` | Webhook (`/webhook/travel-plan-orchestrator`) | Coordinates end-to-end trip planning workflow, delegating to sub-workflows. |
| **02** | `02-flight-research.json` | Sub-workflow / Webhook | Queries flight pricing, validates airport codes, normalizes cabin classes. |
| **03** | `03-hotel-research.json` | Sub-workflow / Webhook | Fetches accommodation availability, nightly prices, and star ratings. |
| **04** | `04-destination-discovery.json` | Sub-workflow / Webhook | Pulls verified attractions, culinary spots, coordinates, and hours. |
| **05** | `05-ai-itinerary-generation.json` | Sub-workflow / Webhook | Grounded Gemini LLM prompt execution to synthesize day-by-day itineraries. |
| **06** | `06-budget-optimization.json` | Sub-workflow / Webhook | Applies financial guardrails, calculates variance, optimizes allocations. |
| **07** | `07-trip-modification.json` | Webhook (`/webhook/trip-modification`) | Processes traveler change requests (dates, budget shifts, activity swaps). |
| **08** | `08-whatsapp-travel-assistant.json` | Twilio / WhatsApp Webhook | Conversational travel assistant receiving and replying to WhatsApp messages. |
| **09** | `09-email-notifications.json` | Webhook (`/webhook/email-notifications`) | Delivers HTML itinerary confirmations and booking summaries via SMTP/SendGrid. |
| **10** | `10-scheduled-travel-reminders.json` | Cron (`0 8 * * *`) / Webhook | Daily check for upcoming trips (e.g., T-7 days, T-24 hours) sending alerts. |
| **11** | `11-error-handling-recovery.json` | Error Trigger | Global n8n error workflow capturing failed executions and alerting admin. |

---

## 3. Deployment with Docker Compose

n8n is fully configured as a containerized service in [`docker-compose.yml`](file:///c:/Users/USER/OneDrive/Desktop/n8n/travelmind-ai/docker-compose.yml).

### Starting the n8n Service

To start the n8n container alongside PostgreSQL and Redis:

```bash
# Start all infrastructure services
docker-compose up -d n8n postgres redis

# Check service logs
docker-compose logs -f n8n
```

### Configuration Environment Variables

Configured in your `.env` (derived from [`.env.example`](file:///c:/Users/USER/OneDrive/Desktop/n8n/travelmind-ai/.env.example)):

```dotenv
# n8n General Configuration
# Internal container port stays 5678; host port is mapped to 5600
# Note: On Windows, ports 5627-5826 are frequently reserved by WinNAT / Hyper-V.
# Host port 5600 avoids conflicts while keeping internal container port at 5678.
N8N_HOST_PORT=5600
N8N_PORT=5678
N8N_PROTOCOL=http
N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=true
N8N_BLOCK_ENV_ACCESS_IN_NODE=false
WEBHOOK_URL=http://localhost:5600/

# TravelMind <-> n8n Integration Security
# Docker-internal network communication uses port 5678 directly:
N8N_HOST=http://n8n:5678
N8N_WEBHOOK_URL=http://n8n:5678/webhook/travel-plan-orchestrator
N8N_WEBHOOK_SECRET=travelmind-n8n-secret
TRAVELMIND_API_BASE_URL=http://api:8000
```

Once running, access the n8n Editor UI at: **`http://localhost:5600`**

---

## 4. Workflow Import Instructions

### Option A: Via the n8n UI (Recommended for First-Time Setup)

1. Open your browser and navigate to `http://localhost:5600`.
2. Complete the initial admin account setup if this is your first run.
3. Click the **Workflows** tab on the left sidebar.
4. Click the **...** menu (top right) and select **Import from File**.
5. Select the JSON files in the `n8n/workflows/` directory one by one.
6. Toggle the **Active** switch in the top right corner of each workflow to activate webhook triggers.

### Option B: Via n8n CLI (Bulk Automation)

If running in Docker:

```bash
# 1. Import workflows from mounted volume (/data/workflows/)
docker compose exec n8n n8n import:workflow --input=/data/workflows/main-travel-planning-orchestrator.json

# 2. Publish workflows to make webhooks live
docker compose exec n8n n8n publish:workflow --id=travelmind-wf-01

# 3. Restart n8n to reload webhook registry
docker compose restart n8n
```

Or on local n8n installation:

```bash
n8n import:workflow --separate --input=./n8n/workflows/
```

---

## 5. Credential Configuration in n8n

After importing the workflows, configure the following credentials in the n8n UI (**Settings > Credentials > New**):

### 1. Google Gemini API
- **Type**: Header Auth or HTTP Query Auth
- **Header Name**: `x-goog-api-key`
- **Value**: Your Google Gemini API Key (`GEMINI_API_KEY`)

### 2. Amadeus Flight & Hotel API
- **Type**: OAuth2 API or Custom HTTP Request
- **Grant Type**: Client Credentials
- **Access Token URL**: `https://test.api.amadeus.com/v1/security/oauth2/token`
- **Client ID**: `AMADEUS_API_KEY`
- **Client Secret**: `AMADEUS_API_SECRET`

### 3. TravelMind Backend Authentication
- **Type**: Header Auth
- **Header Name**: `X-N8N-Webhook-Secret`
- **Value**: The value of `N8N_WEBHOOK_SECRET` defined in your `.env`

### 4. Email Service (SMTP or SendGrid)
- **Type**: SMTP or SendGrid API
- **Host**: `smtp.sendgrid.net` (or your mail server)
- **Port**: `587`
- **User / Password**: Set from `SMTP_USER` and `SMTP_PASSWORD`

### 5. WhatsApp (Twilio / Meta Cloud API)
- **Type**: Twilio API or WhatsApp Business Cloud API
- **Account SID & Auth Token**: From your Twilio / Meta developer console.

---

## 6. Bidirectional Communication & Security Architecture

FastAPI provides dedicated router endpoints in [`backend/app/api/n8n.py`](file:///c:/Users/USER/OneDrive/Desktop/n8n/travelmind-ai/backend/app/api/n8n.py) mounted under `/api/v1/n8n/`:

### 1. FastAPI -> n8n Trigger
When a trip is planned or modified, FastAPI's `trip_service.py` sends a JSON payload to `N8N_WEBHOOK_URL`:
```json
{
  "correlation_id": "c1a85e82-e3a1-432d-98e6-e17f7ad84620",
  "action": "plan_travel",
  "trip_id": "trip_01j7...",
  "destination": "Tokyo, Japan",
  "origin": "SFO",
  "dates": {"start": "2026-04-10", "end": "2026-04-18"},
  "budget": {"amount": 3500, "currency": "USD"},
  "preferences": ["culture", "culinary"],
  "timestamp": "2026-10-05T04:00:00Z"
}
```

### 2. n8n -> FastAPI Callback
n8n reports workflow completion or async enrichment back to:
- **POST** `/api/v1/n8n/webhook/travel-plan`
- **POST** `/api/v1/n8n/webhook/trip-modification`
- **POST** `/api/v1/n8n/webhook/notification-status`

**Security Requirements**:
1. All callback requests must present header: `X-N8N-Webhook-Secret: <your_secret>`
2. All callbacks must include a valid `correlation_id` string for tracing.
3. Every execution is audited in the `agent_execution_logs` database table.

---

## 7. Verifying Webhook Endpoints

You can verify the webhook handler locally with `curl` or PowerShell:

```bash
curl -X POST http://localhost:8000/api/v1/n8n/webhook/travel-plan \
  -H "Content-Type: application/json" \
  -H "X-N8N-Webhook-Secret: dev_n8n_secret_change_in_production" \
  -d '{
    "correlation_id": "test-webhook-trace-001",
    "trip_id": "trip-test-01",
    "status": "completed",
    "results": {
      "verified": true,
      "summary": "n8n flight and hotel check succeeded"
    }
  }'
```

Expected response:
```json
{
  "status": "received",
  "correlation_id": "test-webhook-trace-001",
  "action": "travel_plan_callback",
  "timestamp": "2026-10-05T04:22:00.123456Z"
}
```

You can view recorded audit logs at:
- **GET** `/api/v1/n8n/execution-logs` (requires Admin JWT token).
