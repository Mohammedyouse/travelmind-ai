# TravelMind AI — Enterprise Multi-Agent Travel SaaS Platform

[![Live App](https://img.shields.io/badge/Live_App-Launch_Now-00DF8F?style=for-the-badge&logo=vercel&logoColor=white)](https://travelmind-ai-seven.vercel.app)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.3+-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5+-3178C6?style=flat&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![PostgreSQL](https://img.shields.io/badge/Neon_PostgreSQL-16-4169E1?style=flat&logo=postgresql&logoColor=white)](https://neon.tech/)
[![n8n](https://img.shields.io/badge/n8n-Workflow_Automation-EA4B71?style=flat&logo=n8n&logoColor=white)](https://n8n.io/)
[![License](https://img.shields.io/badge/License-Proprietary-blue.svg?style=flat)](LICENSE)

---

## 🌍 TravelMind AI — Try the Live Application

> **No installation or local setup required! You do NOT need to clone this repository, install Node/Python, or configure Docker to use TravelMind AI.**
>
> The complete production application is live in the cloud and accessible to anyone right now:
>
> ### 👉 [Launch TravelMind AI → https://travelmind-ai-seven.vercel.app](https://travelmind-ai-seven.vercel.app) 👈

### 🚀 Quick Start Guide (Under 60 Seconds in Your Browser):

1. **Open the Application**: Click the live link above to open TravelMind AI in any browser.
2. **Create a Free Account**:
   - Click **"Sign In"** in the top navigation bar.
   - Switch to **"Register"** and enter your name, email, and a secure password.
   - Your account and subscription quota are immediately created in our cloud **Neon PostgreSQL** database.
3. **Launch the Trip Planning Studio**:
   - Click **"Plan New Journey"** on the dashboard to open the interactive 4-step wizard.
4. **Configure Your Journey**:
   - **Step 1**: Choose or type your origin and destination (e.g. *Tokyo*, *Paris*, *Goa*, *Kyoto*, *New York*, or *Jaipur*).
   - **Step 2**: Select your departure and return dates along with number of travelers.
   - **Step 3**: Set your target budget and preferred currency (e.g. `USD`, `EUR`, `INR`, `GBP`).
   - **Step 4**: Pick your travel style and interest tags (e.g. *Culture*, *Culinary*, *Adventure*, *Architecture*).
5. **Generate Verified Plan ⚡**:
   - Click **"Generate Verified Plan"** to trigger the **8-Agent Swarm**.
   - Review your structured day-by-day itinerary, flight intelligence, hotel tiers, landmarks, real-time weather forecasts, and currency breakdown.
6. **Chat with AI Concierge**:
   - Use the **Assistant Chat** tab to ask destination-specific questions regarding packing lists, local etiquette, transit advice, or hidden gems.
7. **Export Itinerary**:
   - Export your personalized travel plan as a formatted printable HTML document or download structured JSON.

---

## 🌐 Verified Live Cloud Endpoints

All live production endpoints are verified, active, and publicly accessible:

| Service / Resource | Production URL | Description | Status |
| :--- | :--- | :--- | :--- |
| **Web Application UI** | [travelmind-ai-seven.vercel.app](https://travelmind-ai-seven.vercel.app) | React 18 + Vite Production Single Page Application | **Active (200 OK)** |
| **Backend Health Check** | [travelmind-ai-seven.vercel.app/health](https://travelmind-ai-seven.vercel.app/health) | FastAPI root health check endpoint | **Active (200 OK)** |
| **API v1 Health** | [travelmind-ai-seven.vercel.app/api/v1/health](https://travelmind-ai-seven.vercel.app/api/v1/health) | Versioned API status check | **Active (200 OK)** |
| **Interactive API Docs (Swagger)** | [travelmind-ai-seven.vercel.app/docs](https://travelmind-ai-seven.vercel.app/docs) | Interactive OpenAPI documentation & testing console | **Active (200 OK)** |
| **OpenAPI Schema** | [travelmind-ai-seven.vercel.app/openapi.json](https://travelmind-ai-seven.vercel.app/openapi.json) | Complete machine-readable API specification (38 endpoints) | **Active (200 OK)** |
| **GitHub Source Repository** | [github.com/Mohammedyouse/travelmind-ai](https://github.com/Mohammedyouse/travelmind-ai) | Official source repository (`main` branch) | **Active (200 OK)** |

---

## 📖 Project Overview

**TravelMind AI** is an intelligent, multi-agent AI Travel SaaS platform providing verified, end-to-end travel research, planning, budgeting, and itinerary generation.

Traditional AI travel tools suffer from common flaws: they hallucinate non-existent flights, invent hotel rates, schedule impossible transit legs, and cannot calculate accurate budgets. 

TravelMind AI solves this by coupling **Google Gemini** with **real-world provider APIs** (Amadeus, OpenStreetMap Nominatim, Open-Meteo, Frankfurter), **8 specialized AI agents**, deterministic financial budgeting rules, and **n8n operational workflow automation**.

---

## 🤖 The 8 Specialized AI Agents

Rather than passing a single prompt to a generic LLM, TravelMind AI divides travel synthesis into eight discrete, domain-specialized agents arranged in a dependency-aware Directed Acyclic Graph (DAG):

```
                                 [ Traveler Input / TripSpec ]
                                               │
                                               ▼
                                   ┌───────────────────────┐
                                   │ 1. Travel Concierge   │
                                   └───────────┬───────────┘
                                               │
               ┌───────────────────────────────┼───────────────────────────────┐
               ▼                               ▼                               ▼
    ┌──────────────────────┐        ┌──────────────────────┐        ┌──────────────────────┐
    │ 2. Flight Intel      │        │ 3. Accommod. Intel   │        │ 4. Destination Disc. │
    └──────────┬───────────┘        └──────────┬───────────┘        └──────────┬───────────┘
               │                               │                               │
               │                               │               ┌───────────────┴───────────────┐
               │                               │               ▼                               ▼
               │                               │    ┌──────────────────────┐        ┌──────────────────────┐
               │                               │    │ 5. Transport & Route │        │ 7. Personalization   │
               │                               │    └──────────┬───────────┘        └──────────┬───────────┘
               │                               │               │                               │
               └───────────────────────┬───────┴───────────────┴───────────────────────────────┘
                                       ▼
                            ┌──────────────────────┐
                            │ 6. Budget Intel      │
                            └──────────┬───────────┘
                                       │
                                       ▼
                            ┌──────────────────────┐
                            │ 8. Travel Support    │
                            └──────────┬───────────┘
                                       │
                                       ▼
                       [ Final Grounded Verified Itinerary ]
```

### 1. Travel Concierge Agent
* **Role**: Primary intake and conversational coordinator.
* **Function**: Validates input parameters, verifies required fields (`origin`, `destination`, `budget`, `currency`), prompts for missing context, and provides expert contextual advice in real time.

### 2. Flight Intelligence Agent
* **Role**: Aviation and flight validation specialist.
* **Function**: Interfaces with Amadeus Self-Service APIs to resolve IATA origin/destination airport codes, queries live flight itineraries, calculates flight durations, and estimates realistic round-trip ticket costs.

### 3. Accommodation Intelligence Agent
* **Role**: Lodging and hospitality specialist.
* **Function**: Discovers vetted accommodations across budget tiers (hostel, boutique, luxury) with estimated nightly rates and neighborhood ratings.

### 4. Destination Discovery Agent
* **Role**: Geographical and point-of-interest (POI) explorer.
* **Function**: Queries live OpenStreetMap (Nominatim) to geocode coordinates, discover verified local landmarks, cultural attractions, parks, and viewpoints.

### 5. Transportation & Route Planning Agent
* **Role**: Pacing and transit architect.
* **Function**: Organizes attractions into logical geographical clusters, generates realistic daily schedules (Morning, Afternoon, Evening), and computes transit times to minimize backtracking.

### 6. Budget Intelligence Agent
* **Role**: Deterministic financial auditor.
* **Function**: Aggregates flight, accommodation, attraction, dining, and transit expenses; converts foreign exchange via live rates; applies a dynamic 10% contingency buffer; and verifies that total costs remain within the traveler's budget.

### 7. Personalization & Recommendation Agent
* **Role**: Traveler preference alignment specialist.
* **Function**: Tailors landmark selection, dining recommendations, and activity pacing to match the traveler's declared interests (culinary, architecture, adventure, wellness).

### 8. Travel Support Agent
* **Role**: Weather, safety, and checklist specialist.
* **Function**: Fetches real-time multi-day forecasts from the Open-Meteo REST API, generates destination-specific packing checklists, and delivers localized safety tips and cultural etiquette guidance.

### How the Agents Influence One Another:
* **Constraint Propagation**: If the **Flight** and **Accommodation** agents consume 70% of the total budget, the **Budget Agent** signals the **Transportation & Route Agent** and **Destination Discovery Agent** to prioritize free landmarks, public transit, and casual dining.
* **Geographical Pacing**: The **Route Planning Agent** uses the exact latitude and longitude resolved by the **Destination Discovery Agent** to ensure that morning and afternoon activities are located within walkable or short-transit corridors.
* **Climate Adaptation**: The **Travel Support Agent** uses forecast data from Open-Meteo to inform the **Itinerary Generator** to schedule indoor cultural visits during rainy days and outdoor excursions during clear weather.

---

## 🏛️ System & Cloud Architecture

TravelMind AI runs on a **100% $0/month modern cloud architecture**:

```
                                  USER BROWSER
                                       │
                                       ▼
                     https://travelmind-ai-seven.vercel.app
                   ┌───────────────────┴───────────────────┐
                   │                                       │
            /(.*)  │                                /api/* │ /health │ /docs
                   ▼                                       ▼
           React 18 / Vite SPA                     FastAPI ASGI Backend
        (Static Optimized Assets)              (Serverless Python 3.12 Engine)
                                                           │
                                          SSL Pooler       │
                                     ┌─────────────────────┴─────────────────────┐
                                     ▼                                           ▼
                             Neon PostgreSQL                              Local n8n Studio
                         (12 Schema Tables)                           (http://localhost:5600)
```

* **Vercel Multi-Service Hosting**: The React client and FastAPI ASGI backend are co-located under a single unified domain using [`vercel.json`](file:///c:/Users/USER/OneDrive/Desktop/n8n/travelmind-ai/vercel.json), eliminating cross-origin issues and browser restrictions.
* **Neon PostgreSQL**: Managed serverless PostgreSQL database hosted in AWS US-East-2 with connection pooling and SSL encryption.
* **Local n8n Workflow Automation**: Executes on Docker (`localhost:5600`), communicating securely with the cloud backend via HMAC secret verification.

---

## 💻 Technology Stack

* **Frontend**: React 18, TypeScript, Vite, Vanilla CSS design system (dark-mode glassmorphic aesthetics, responsive mobile navigation).
* **Backend**: FastAPI 0.115+, Python 3.12, Pydantic, Uvicorn, HTTPX.
* **Database & ORM**: PostgreSQL 16 (Neon Cloud) / SQLite (Local dev), SQLAlchemy, Alembic migrations.
* **AI & Machine Learning**: Google Gemini 2.0 Flash (`gemini-2.0-flash`), custom deterministic fallback synthesizer.
* **External APIs**: Amadeus GDS, OpenStreetMap Nominatim, Open-Meteo Weather, Frankfurter FX.
* **Workflow Automation**: n8n Automation Engine (11 production workflows).
* **Containerization**: Docker, Docker Compose.

---

## 🗄️ Database Architecture (Neon PostgreSQL)

The production schema contains **12 tables** managed via Alembic:

| Table | Description |
| :--- | :--- |
| `users` | User accounts, hashed passwords (bcrypt), and roles (`traveler`, `admin`) |
| `trips` | Trip records, itineraries, origin, destination, dates, budget, currency, and agent results |
| `subscriptions` | SaaS subscription tiers (`free`, `pro`, `enterprise`) and quotas |
| `notifications` | In-app user notifications and system alerts |
| `payments` | Payment transactions and billing records |
| `conversations` | AI Concierge chat message history linked to users and trips |
| `itinerary_items` | Day-by-day activities, time slots, locations, and costs |
| `budget_snapshots` | Aggregated financial breakdowns and contingency reserves |
| `preferences` | Traveler personal preferences (interests, diet, pace) |
| `provider_search_records` | Audit log of external API calls and provider responses |
| `agent_execution_logs` | Performance metrics, durations, and status of agent DAG executions |
| `alembic_version` | Current database migration version tracking |

---

## 🔄 n8n Workflow Automation

TravelMind AI includes **11 production n8n workflows** located in [`n8n/workflows/`](file:///c:/Users/USER/OneDrive/Desktop/n8n/travelmind-ai/n8n/workflows):

1. **`01 - Main Travel Planning Orchestrator`**: Master webhook router that coordinates multi-agent research.
2. **`02 - Flight Research`**: Queries and validates flight options.
3. **`03 - Hotel Research`**: Searches vetted lodging options.
4. **`04 - Destination Discovery`**: Resolves landmarks and points of interest.
5. **`05 - AI Itinerary Generation`**: Orchestrates day-by-day schedule synthesis.
6. **`06 - Budget Optimization`**: Performs currency conversions and budget audits.
7. **`07 - Trip Modification`**: Recalculates itineraries when dates or budgets change.
8. **`08 - WhatsApp Travel Assistant`**: Delivers updates via messaging webhooks.
9. **`09 - Email Notifications`**: Formats and sends booking confirmations.
10. **`10 - Scheduled Travel Reminders`**: Automated notifications prior to departure dates.
11. **`11 - Error Handling and Recovery`**: Automatic retries and fallback error alerts.

---

## 🛠️ Local Installation & Development

> **Reminder**: Running locally is only required for developers contributing to the codebase. General users can use the [Live Application](https://travelmind-ai-seven.vercel.app/) directly in their browser.

### Prerequisites:
* Python 3.11+
* Node.js 18+ and npm
* Docker & Docker Compose (optional for standalone dev, recommended for n8n)

### 1. Clone & Set Up Environment:
```bash
git clone https://github.com/Mohammedyouse/travelmind-ai.git
cd travelmind-ai
cp .env.example .env
```

### 2. Backend Setup:
```bash
cd backend
python -m venv venv

# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
alembic upgrade head
uvicorn app.api.app:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation will be available locally at `http://localhost:8000/docs`.

### 3. Frontend Setup:
```bash
cd ../frontend
npm install
npm run dev
```
The local client will be available at `http://localhost:5173`.

### 4. Running the Full Stack with Docker:
```bash
docker compose up -d
```

| Service | Local URL |
| :--- | :--- |
| **Frontend** | `http://localhost:5173` |
| **Backend API** | `http://localhost:8000` |
| **n8n Studio** | `http://localhost:5600` |
| **PostgreSQL** | `localhost:5433` |
| **Redis** | `localhost:6379` |

---

## 🔑 Safe Environment Configuration (`.env.example`)

Copy [`.env.example`](file:///c:/Users/USER/OneDrive/Desktop/n8n/travelmind-ai/.env.example) to `.env` to configure local or deployment settings:

```dotenv
# Application & Authentication
APP_ENV=development
JWT_SECRET_KEY=change-me-to-a-secure-random-32-byte-hex-string
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Database Persistence
DATABASE_URL=sqlite:///./travelmind.db
POSTGRES_DB=travelmind
POSTGRES_USER=travelmind
POSTGRES_PASSWORD=travelmind
POSTGRES_HOST_PORT=5433

# Caching
REDIS_URL=redis://localhost:6379/0

# Optional Provider Credentials
GEMINI_API_KEY=               # Free at https://aistudio.google.com
AMADEUS_CLIENT_ID=            # Free at https://developers.amadeus.com
AMADEUS_CLIENT_SECRET=
AMADEUS_BASE_URL=https://test.api.amadeus.com

# n8n Automation Engine Integration
N8N_HOST_PORT=5600
N8N_HOST=http://localhost:5600
WEBHOOK_URL=http://localhost:5600/
N8N_WEBHOOK_URL=http://localhost:5600/webhook/travel-plan-orchestrator
N8N_WEBHOOK_SECRET=travelmind-n8n-secret
TRAVELMIND_API_BASE_URL=http://localhost:8000

# Frontend Client
VITE_API_BASE_URL=http://localhost:8000
```

---

## ⚠️ Current Limitations & External Requirements

* **Live Flight Booking**: Live Amadeus search is configured to connect to Amadeus Self-Service APIs. When credentials are not set, the Flight Intelligence Agent gracefully defaults to an unconfigured state and estimated market flight models without crashing.
* **Gemini LLM Key**: When a `GEMINI_API_KEY` is provided, itineraries and chat responses utilize live Gemini 2.0 Flash. When omitted, TravelMind AI uses a deterministic grounded research synthesis engine with zero hallucinations.
* **Serverless Execution Timeout**: Vercel Hobby serverless functions have a 10-second default execution window. The TravelMind AI agent pipeline is designed with efficient asynchronous parallel requests to complete within this window.

---

## 🧪 Automated Test Suite

TravelMind AI maintains a strict 100% test passing standard across all modules:

```bash
# Run backend test suite (53 tests)
python -m unittest discover -s backend/tests -p "test_*.py"

# Run data science pipeline tests (8 tests)
python -m unittest discover -s data_science/tests -p "test_*.py"

# Build and validate frontend TypeScript
cd frontend && npm run build
```

---

## 📄 License

Proprietary software — TravelMind AI Team. All rights reserved.
