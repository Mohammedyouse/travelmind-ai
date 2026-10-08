# TravelMind AI — Implementation Roadmap

_Version: 2.0 | Status: Active Execution_

This roadmap defines the phase-by-phase implementation plan to evolve TravelMind AI into a full-featured, secure, production-grade AI Travel SaaS platform.

---

## Phase 1: Repository Audit & Architecture Correction [COMPLETED]
- [x] Comprehensive inspection of backend, frontend, agents, data science, n8n, and deployment assets.
- [x] Run and verify existing test suites: 40 backend tests passed, 8 data science tests passed, frontend Vite build passed.
- [x] Confirm database integrity rules (no destructive resets).
- [x] Document repository audit findings in `PROJECT_AUDIT.md`.
- [x] Align system architecture in `docs/ARCHITECTURE.md`.
- [x] Update `PROJECT_STATUS.md` with active development status.

---

## Phase 2: Real Travel Data & Provider Integration [IN PROGRESS]
- [ ] **Flight Intelligence**:
  - Integrate Amadeus flight provider with city/IATA resolution.
  - Implement full flight search request handling (origin, destination, dates, adults, currency).
  - Normalize results (carrier, flight number, departures, arrivals, stops, duration, real price, retrieval timestamp).
  - Honest unconfigured / error handling when credentials are missing or network fails.
- [ ] **Accommodation Intelligence**:
  - Implement modular `HotelProvider` architecture with Amadeus Hotel Search & directory provider.
  - Support destination, check-in, check-out, guests, room type, rating, real price, currency, amenities.
- [ ] **Destination Intelligence**:
  - Implement live `PlaceProvider` using OpenStreetMap (Nominatim & Overpass API) + Google Places adapter.
  - Retrieve real attractions, restaurants, coordinates (lat/lng), addresses, categories, ratings, opening hours.
- [ ] **Weather & Currency Intelligence**:
  - Implement live `WeatherProvider` using Open-Meteo REST API (real forecasts, temperatures, conditions, no API key needed).
  - Implement live `CurrencyProvider` using Frankfurter / open.er-api.com (real exchange rates, conversion calculations, no API key needed).
  - Record provider timestamps and source references.

---

## Phase 3: Gemini-Powered Itinerary Generation
- [ ] Connect `GeminiClient` in `backend/app/llm/base.py` to the core travel planning pipeline.
- [ ] Assemble rich prompt context incorporating:
  - Validated trip specifications and traveler preferences.
  - Real flight offers retrieved.
  - Real accommodation options discovered.
  - Real attractions and dining options found.
  - Live weather forecasts and local currency exchange rates.
- [ ] Enforce structured JSON output matching day-by-day itinerary schema (morning, afternoon, evening slots, transit notes, cost estimates).
- [ ] Implement robust retries and schema validation in `LLMGateway`.
- [ ] Provide research-grounded synthesis fallback when Gemini API key is unconfigured.

---

## Phase 4: Complete the Eight AI Agents & Dependency DAG
- [ ] Connect all 8 agents into a structured execution DAG in `TripService`:
  1. **Travel Concierge Agent**: Validates inputs, clarifies traveler needs, enriches trip context.
  2. **Flight Intelligence Agent**: Searches and scores flight options (depends on Concierge).
  3. **Accommodation Intelligence Agent**: Searches and ranks hotel stays (depends on Concierge).
  4. **Destination Discovery Agent**: Fetches real POIs, attractions, restaurants (depends on Concierge).
  5. **Transportation & Route Agent**: Plans local transfers and transit routes (depends on Destination).
  6. **Budget Intelligence Agent**: Synthesizes real itemized costs from flight, hotel, and activity results (depends on Flight, Accommodation, Destination).
  7. **Personalization & Recommendation Agent**: Ranks options against traveler style and interests (depends on Destination, Budget).
  8. **Travel Support Agent**: Generates packing checklist, visa notes, and scheduled reminders (depends on Concierge, Weather).
- [ ] Ensure typed inputs, outputs, logging, and error boundaries for all 8 agents.
- [ ] Add unit tests verifying each agent's execution and context propagation.

---

## Phase 5: n8n Workflows & Backend Webhook Integration
- [ ] Author 11 production-ready workflow definitions in `n8n/workflows/`:
  1. `main-travel-planning-orchestrator.json`
  2. `flight-research.json`
  3. `hotel-research.json`
  4. `destination-discovery.json`
  5. `ai-itinerary-generation.json`
  6. `budget-optimization.json`
  7. `trip-modification.json`
  8. `whatsapp-travel-assistant.json`
  9. `email-notifications.json`
  10. `scheduled-travel-reminders.json`
  11. `error-handling-recovery.json`
- [ ] Implement FastAPI n8n integration endpoints:
  - `/api/v1/n8n/webhook`: Secure incoming webhook receiver with `X-N8N-Webhook-Secret`.
  - `/api/v1/n8n/trigger`: Dispatcher to trigger n8n workflows with correlation IDs and timeout handling.
  - `/api/v1/n8n/status`: Workflow execution tracking and history inspection.
- [ ] Add Docker Compose configuration for n8n with persistent volume `n8n_data`.

---

## Phase 6: Complete Frontend User Experience
- [ ] Build a cohesive, modern, glassmorphic UI across all required sections:
  1. **Landing Page**: Hero banner, value proposition, feature showcase, testimonials, pricing plans.
  2. **Authentication**: Register, Login, session persistence, role display.
  3. **User Dashboard**: Stats (total trips, destinations, budget saved), quick actions, active trips.
  4. **Trip Creation Wizard**: Step-by-step wizard (Route -> Dates & Travelers -> Budget & Currency -> Style & Interests).
  5. **AI Travel Assistant**: Interactive chat interface with message history and quick suggestion chips.
  6. **Flight Comparison**: Cards showing real flight options, stops, carriers, departure/arrival times, price tags.
  7. **Hotel Comparison**: Property cards with ratings, prices, amenities, photos/placeholders, location tags.
  8. **Destination Discovery**: Curated attractions, dining, cultural spots with ratings and addresses.
  9. **Interactive Map**: Dynamic visual route map showing origin, destination, and attraction pins.
  10. **Day-by-Day Itinerary**: Accordion/tabbed daily view with morning/afternoon/evening slots and notes.
  11. **Budget Breakdown**: Progress bars, category breakdown, contingency buffer, and currency display.
  12. **Saved Trips & Modification**: Trip management with status badges, edit modal, and delete options.
  13. **Notifications Center**: Real-time alerts, pre-trip reminders, packing alerts.
  14. **User Preferences**: Profile settings, favorite travel styles, dietary restrictions, preferred currencies.
  15. **Subscription Management**: Free vs Pro vs Enterprise tier cards, feature matrix, upgrade trigger.
  16. **Admin Dashboard**: System health metrics, registered users, trips count, provider statuses, execution logs.

---

## Phase 7: Database & Alembic Migrations
- [ ] Extend SQLAlchemy models in `backend/app/models/`:
  - `Subscription` (tier, status, current_period_end, limits).
  - `Payment` (amount, currency, status, provider_ref).
  - `Notification` (type, title, message, status, sent_at).
  - `ProviderSearchRecord` (provider, query, status, timestamp, response_data).
  - `AgentExecutionLog` (agent_name, duration_ms, status, error, context_snapshot).
- [ ] Update `backend/app/db.py` to support full CRUD for all new entities.
- [ ] Create Alembic migration script for PostgreSQL / SQLite schema evolution.

---

## Phase 8: SaaS Features, Security & Export
- [x] Implement subscription tiers & usage limits (Free: 3 trips/month, Pro: unlimited, Enterprise: concierge).
- [x] Implement rate limiting middleware (token bucket / IP-based limits).
- [x] Implement Stripe webhook endpoint for subscription checkout and payment events.
- [x] Implement Itinerary Export: Printable formatted HTML / downloadable JSON itinerary.
- [x] Review security: CORS origin whitelist, JWT signature verification, secret masking in logs.

---

## Phase 9: Docker, DevOps & CI/CD
- [x] Update `docker-compose.yml` to include `n8n` service alongside `db`, `api`, and `frontend`.
- [x] Add health checks, network definitions, and persistent volumes (`postgres_data`, `n8n_data`).
- [x] Provide production-optimized `Dockerfile` for frontend (multi-stage build with nginx).
- [x] Update `.github/workflows/ci.yml` for automated backend tests, data science tests, and frontend build.

---

## Phase 10: End-to-End Testing & Verification
- [x] Add unit and integration tests for:
  - All new provider adapters (Amadeus, Hotels, OSM Places, Open-Meteo, Frankfurter).
  - 8-agent orchestrated DAG execution.
  - Gemini itinerary generation with grounded fallback.
  - n8n webhook authentication and dispatch.
  - Subscription tier limits and Stripe webhook processing.
- [x] Execute full backend test suite (`python -m unittest discover`).
- [x] Execute frontend build (`npm run build`).
- [x] Verify live application endpoints and update `PROJECT_STATUS.md`.
