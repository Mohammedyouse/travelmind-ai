# TravelMind AI — Enterprise AI Travel SaaS Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.3+-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5+-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![n8n](https://img.shields.io/badge/n8n-Workflow%20Automation-EA4B71?logo=n8n&logoColor=white)](https://n8n.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)

**TravelMind AI** is an intelligent, multi-agent AI Travel SaaS platform providing verified, end-to-end travel research, planning, budgeting, and itinerary generation. Unlike generic AI travel wrappers that invent hallucinated flights and fictional hotel rates, TravelMind AI couples **Google Gemini** with **real travel data providers** (Amadeus, Open-Meteo, OpenStreetMap, Frankfurter), **8 specialized AI agents**, deterministic financial budgeting, and **n8n operational workflow automation**.

---

## 🚀 Key Highlights & Capabilities

- 🤖 **8 Autonomous AI Specialist Agents**: Arranged in a dependency-aware Directed Acyclic Graph (DAG) for research, flight validation, hotel matching, destination discovery, route planning, budget calculation, personalization, and travel support.
- ✈️ **Real Travel Data Integrations**:
  - **Flights**: Live Amadeus API adapter with IATA code resolution, airline normalization, duration, and departure/arrival timestamps.
  - **Accommodations**: Amadeus Hotel search and verified destination properties directory.
  - **Attractions & Places**: OpenStreetMap Nominatim geocoding and verified landmarks database with coordinates and opening hours.
  - **Live Weather**: Open-Meteo REST API delivering real-time daily temperature and precipitation forecasts.
  - **Currency & FX**: Frankfurter & Open Exchange Rates API providing live foreign exchange conversion.
- 🧠 **Gemini-Powered Grounded Synthesis**: Generates structured, day-by-day itineraries grounded exclusively in verified provider data to eliminate hallucinations.
- 🔄 **n8n Workflow Automation Engine**: 11 production-ready importable workflows covering travel planning orchestration, flight/hotel research, trip modifications, WhatsApp assistant, email delivery, scheduled reminders, and error alerting.
- 💻 **Complete Modern Frontend (React + TypeScript)**:
  - 16 views and interactive sections: Landing page, Auth, Dashboard, Trip Wizard, Interactive Map, Day-by-Day Itineraries, Flight & Hotel Comparators, Budget Breakdown, AI Assistant Chat, Trip Modification, Notifications, User Preferences, Subscriptions & Pricing, Admin Analytics, and HTML/JSON Itinerary Exports.
  - Dark-mode glassmorphic design system styled in modular Vanilla CSS with zero external UI bloat.
- 🛡️ **Enterprise Security & SaaS Foundation**:
  - JWT token authentication with bcrypt password hashing and Role-Based Access Control (`traveler`, `admin`).
  - Tiered subscription management (`Free`, `Pro`, `Enterprise`) with usage quotas, Stripe checkout integration, and audit logging.
  - SQLAlchemy persistence with Alembic migration scaffolding supporting both local SQLite and production PostgreSQL.

---

## 📐 System Architecture

```mermaid
graph TB
    subgraph ClientLayer ["Frontend (React 18 + TypeScript)"]
        UI[Web Dashboard & Wizard]
        Chat[AI Travel Assistant Chat]
        Map[Interactive Map & Itinerary View]
        AdminUI[Admin Analytics Console]
    end

    subgraph BackendLayer ["Backend API (FastAPI)"]
        Router[FastAPI API Router]
        AuthSvc[Auth & RBAC Service]
        TripSvc[Trip Planning Service]
        N8NRouter[n8n Webhook Gateway]
    end

    subgraph AgentDAG ["8 Autonomous AI Agents (DAG)"]
        A1[1. Travel Concierge]
        A2[2. Flight Intelligence]
        A3[3. Accommodation Intelligence]
        A4[4. Destination Discovery]
        A5[5. Transportation & Route]
        A6[6. Budget Intelligence]
        A7[7. Personalization & Recommender]
        A8[8. Travel Support]
    end

    subgraph ExternalProviders ["Real Providers & Intelligence"]
        Amadeus[Amadeus Flight & Hotel API]
        OSM[OpenStreetMap / Nominatim]
        Meteo[Open-Meteo Weather API]
        FX[Frankfurter FX API]
        Gemini[Google Gemini 2.0 Flash]
    end

    subgraph Automation ["n8n Workflow Automation"]
        N8NEngine[n8n Automation Engine]
        WF1[Orchestrator Workflow]
        WF2[WhatsApp Travel Assistant]
        WF3[Scheduled Reminders & Alerts]
    end

    subgraph Storage ["Persistence Layer"]
        DB[(PostgreSQL / SQLite)]
    end

    UI --> Router
    Chat --> Router
    Router --> AuthSvc
    Router --> TripSvc
    Router <-->|HMAC Webhooks| N8NRouter
    N8NRouter <--> N8NEngine
    N8NEngine --> WF1
    N8NEngine --> WF2
    N8NEngine --> WF3

    TripSvc --> AgentDAG
    A1 --> A2 & A3 & A4 & A8
    A4 --> A5 & A7
    A2 & A3 & A4 --> A6

    A2 --> Amadeus
    A3 --> Amadeus
    A4 --> OSM
    A6 --> FX
    A8 --> Meteo
    TripSvc --> Gemini

    Router --> DB
    AuthSvc --> DB
```

For in-depth architectural specifications, see [`docs/ARCHITECTURE.md`](file:///c:/Users/USER/OneDrive/Desktop/n8n/travelmind-ai/docs/ARCHITECTURE.md).

---

## 🛠️ Tech Stack & Directory Structure

```
travelmind-ai/
├── backend/
│   ├── app/
│   │   ├── agents/            # 8 Autonomous AI Specialist Agents
│   │   ├── api/               # FastAPI routers (app.py, n8n.py)
│   │   ├── integrations/      # Real Providers (Amadeus, Meteo, FX, OSM, Gemini)
│   │   ├── models/            # SQLAlchemy models (trip.py, saas.py)
│   │   ├── services/          # Trip planning, orchestrator, budget engine
│   │   ├── auth.py            # Password hashing, JWT issuance & verification
│   │   └── db.py              # SQLite / PostgreSQL connection and SaaS CRUD
│   ├── migrations/            # Alembic database migrations
│   └── tests/                 # Backend automated unit and integration tests
├── data_science/              # Recommendation, ranking, and budget optimization
├── frontend/
│   ├── src/
│   │   ├── components/        # 11 React components (Wizard, Map, Assistant, etc.)
│   │   ├── services/          # Axios API service client
│   │   ├── App.tsx            # Main application router and state management
│   │   └── styles.css         # Glassmorphic dark styling design system
├── n8n/
│   └── workflows/             # 11 Production importable n8n workflows (.json)
├── docs/                      # Architectural specs & n8n setup manual
├── scripts/                   # End-to-end smoke tests and utility scripts
└── docker-compose.yml         # Container definitions (backend, frontend, db, n8n)
```

---

## 🚦 Quickstart: Running Locally

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- Docker & Docker Compose (optional for local dev, required for full stack containerization)

### 1. Backend Setup

```bash
# Navigate to the backend directory
cd backend

# Create and activate a virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp ../.env.example ../.env

# Run database migrations
alembic upgrade head

# Start the FastAPI development server
uvicorn app.api.app:app --host 0.0.0.0 --port 8000 --reload
```

The interactive OpenAPI documentation will be accessible at: **`http://localhost:8000/docs`**

### 2. Frontend Setup

```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies
npm install

# Start the Vite development server
npm run dev
```

The web application will be accessible at: **`http://localhost:5173`**

---

## 🐳 Running with Docker Compose

To run the complete production-oriented stack including FastAPI, React, PostgreSQL, Redis, and n8n:

```bash
# Build and start all services in detached mode
docker-compose up -d --build

# View container status
docker-compose ps
```

| Service | Local URL | Description |
|---|---|---|
| **Frontend UI** | `http://localhost:5173` | React Client Application |
| **Backend API** | `http://localhost:8000` | FastAPI Backend & `/docs` |
| **n8n Automation** | `http://localhost:5600` | n8n Workflow Editor & Webhooks (Host: `5600`, Container: `5678`) |
| **PostgreSQL** | `localhost:5433` (mapped from 5432) | Production Database Engine |
| **Redis Cache** | `localhost:6379` | Distributed Cache & Session Store |

For detailed instructions on configuring and importing the 11 n8n workflows, see [`docs/N8N_SETUP.md`](file:///c:/Users/USER/OneDrive/Desktop/n8n/travelmind-ai/docs/N8N_SETUP.md).

---

## 🧪 Testing & Verification

The repository includes a comprehensive automated test suite spanning backend services, agent DAG orchestration, live provider normalization, n8n webhooks, data science modules, and frontend type-checking:

```bash
# Run all backend unit & integration tests (48 tests)
python -m unittest discover -s backend/tests -p "test_*.py"

# Run all data science tests (8 tests)
python -m unittest discover -s data_science/tests -p "test_*.py"

# Run frontend TypeScript verification and production build
cd frontend
npm run build

# Run end-to-end live services verification test
python scripts/test_live_services.py
```

---

## 🔑 Environment Configuration

Create a `.env` file in the root directory (based on [`.env.example`](file:///c:/Users/USER/OneDrive/Desktop/n8n/travelmind-ai/.env.example)):

```dotenv
# Backend Configuration
SECRET_KEY=generate_a_secure_jwt_secret_key_here
DATABASE_URL=sqlite:///./travelmind.db # or postgresql+psycopg://travelmind:travelmind@localhost:5433/travelmind
ENVIRONMENT=development

# Google Gemini API
GEMINI_API_KEY=your_gemini_api_key_here

# Amadeus Flight & Hotel API
AMADEUS_CLIENT_ID=your_amadeus_api_key_here
AMADEUS_CLIENT_SECRET=your_amadeus_api_secret_here

# n8n Automation Engine
N8N_HOST_PORT=5600
N8N_WEBHOOK_URL=http://localhost:5600/webhook/travel-plan-orchestrator
N8N_WEBHOOK_SECRET=travelmind-n8n-secret
TRAVELMIND_API_BASE_URL=http://localhost:8000

# Stripe Payment Gateway
STRIPE_SECRET_KEY=sk_test_placeholder_key
STRIPE_WEBHOOK_SECRET=whsec_placeholder_secret
```

---

## 📄 License
Proprietary software — TravelMind AI Team. All rights reserved.
