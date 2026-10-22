# TravelMind AI — Travel Data Integration Status

This document provides a transparent, audit-ready status of all third-party travel data integrations, external APIs, and agent providers in TravelMind AI.

---

## 📊 Summary Status Matrix

| Category | Provider | Status | Environment Variable(s) | Behavior When Unconfigured | Behavior When Configured |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Flights** | Amadeus Self-Service Flight Offers v2 | ⚠️ Unconfigured (Transparent Fallback) | `AMADEUS_CLIENT_ID`<br>`AMADEUS_CLIENT_SECRET`<br>`AMADEUS_BASE_URL` | Status `unconfigured`. Generates direct Google Flights dynamic search link with exact resolved IATA codes and dates. Zero fabricated flight offers. Corridor baseline used for budget estimate. | Queries live Amadeus OAuth2 token + REST endpoint `/v2/shopping/flight-offers`. Parses real fares, carrier names, flight numbers, stops, and schedules. |
| **Accommodations** | Verified Destination Hotels / Amadeus Hotel Search | 🟢 Active (Verified Dataset + Rate Benchmark) | `AMADEUS_CLIENT_ID`<br>`AMADEUS_CLIENT_SECRET` (optional) | Curated verified properties across budget hostels, mid-range boutique havelis, and 5-star luxury heritage stays across major world and Indian cities (Goa, Jaipur, Delhi, Mumbai, Udaipur, Varanasi, Manali, Paris, London, Tokyo, Lisbon, NYC, Dubai). Nightly rates converted via real FX. Direct Google Hotels search link. Clearly tagged `pricing_type: estimated_reference_rate`. Zero fabricated availability. | Queries live Amadeus Hotel Search if credentials configured, falling back seamlessly to verified property directory. |
| **Destinations & Attractions** | OpenStreetMap Nominatim & Overpass / Verified Places Directory | 🟢 Live Active | `PLACES_API_KEY` (optional) | Live geocoding via OpenStreetMap Nominatim REST API with fallback to verified destination points of interest with real latitude/longitude coordinates, ratings, and categories. | Augments POI searches with Google Places API if `PLACES_API_KEY` is provided. |
| **Interactive Maps** | Leaflet + OpenStreetMap Tile Layer | 🟢 Live Active | None (Zero keys required) | 100% live interactive map markers matching real coordinates of discovered attractions and accommodations. Custom pins for landmarks, hotels, and viewpoints with popup info cards. | N/A (Always live and free). |
| **Weather Forecasts** | Open-Meteo REST API | 🟢 Live Active | None (Zero keys required) | Fetches real-time multi-day weather forecasts, temperatures (°C), precipitation probabilities, and climate conditions based on exact destination latitude/longitude. Weather-tailored packing checklists generated dynamically. | If departure date is beyond the 14-day forecast horizon, destination current conditions and reference weather are displayed with clear horizon disclosure. |
| **Foreign Exchange (FX)** | open.er-api.com & Frankfurter | 🟢 Live Active | None (Zero keys required) | Real-time exchange rates for USD, EUR, GBP, INR, JPY, CAD, AUD, etc. Cached with timestamp. Fallback to reference table if offline. | Live multi-currency conversion applied across all budget calculations and accommodation pricing. |
| **AI Itinerary Synthesis** | Google Gemini 2.0 Flash / Multi-Agent Grounded Engine | 🟢 Active (Dual Mode) | `GEMINI_API_KEY` | Deterministic Multi-Agent synthesis compiles rich day-by-day itinerary (`ItineraryCompilerAgent`) grounded strictly in verified researched attractions, hotels, transit tips, and local dining. Labeled `source: grounded_research_multi_agent`. Zero LLM hallucinations. | When `GEMINI_API_KEY` is supplied, prompts Gemini 2.0 Flash structured JSON synthesis with strict schema validation, grounded in the researched places and hotel context. |
| **Authentication & Database** | JWT + SQLite / Neon PostgreSQL | 🟢 Live Active | `JWT_SECRET_KEY`<br>`DATABASE_URL` | Local SQLite database (`travelmind.db`) with automatic schema initialization, user authentication, bcrypt password hashing, and token expiration handling. | Production PostgreSQL (Neon) connection with connection pooling and schema migrations. |
| **SaaS Billing & Subscriptions** | Stripe Checkout & Webhooks | 🟢 Active (Test Mode & Webhook Ready) | `STRIPE_SECRET_KEY`<br>`STRIPE_WEBHOOK_SECRET` | Generates safe test-mode checkout sessions (`cs_test_*`), processes subscription webhooks (`checkout.session.completed`), creates payment records, updates user quota, and sends in-app notifications. Never triggers unapproved charges. | Full live payment processing when real production Stripe keys are configured. |

---

## 🔍 Detailed Provider Breakdown

### 1. Flight Intelligence (`FlightIntelligenceAgent`)
- **API Endpoint**: `https://test.api.amadeus.com/v2/shopping/flight-offers`
- **Authentication**: OAuth 2.0 Client Credentials (`client_id`, `client_secret`)
- **Airport Resolution**: Maps city names and IATA codes across 50+ major international and domestic hubs (e.g. `DEL`, `BOM`, `GOI`, `GOX`, `JAI`, `PAR`, `LON`, `TYO`, `NYC`).
- **Transparency Guarantee**:
  - If Amadeus credentials are not present in `.env`, the agent outputs `status: "unconfigured"` with a helpful guidance message.
  - A dynamic direct search URL (e.g., `https://www.google.com/travel/flights?q=flights+from+DEL+to+GOI+on+2026-11-01+return+2026-11-05`) is provided so travelers can check real-time airline pricing immediately.
  - Flight prices in the budget are labeled `unconfigured_provider_estimate` and never marked as verified quotes.

### 2. Accommodation Intelligence (`AccommodationIntelligenceAgent`)
- **Data Source**: Vetted destination property directory covering:
  - Budget hostels (Zostel, The Hosteller, goSTOPS, Generator, UNPLAN, Wombat's, Pod 51)
  - Mid-range heritage boutiques (Umaid Bhawan, Amet Haveli, Old Harbour Hotel, Bloomrooms, etc.)
  - 4-star and 5-star heritage palaces and luxury resorts (Rambagh Palace, Taj Lake Palace, Leela Palace, The Plaza, Le Meurice, The Savoy)
- **Pricing Calculation**:
  - Nightly reference prices are converted dynamically to the user's selected currency using live exchange rates.
  - Taxes and fees are calculated at 12% standard hospitality tax.
  - Room counts scale dynamically: `rooms = max(1, (travelers + 1) // 2)`.
  - Stays include neighborhood location, verified amenities list, and direct Google Hotels booking query link.
  - Every property card displays `pricing_type: "estimated_reference_rate"` with the disclaimer: *"Live pricing unavailable (Amadeus unconfigured). Showing verified properties with estimated reference rates."*

### 3. Destination Discovery (`DestinationDiscoveryAgent`)
- **Data Source**: OpenStreetMap Nominatim reverse geocoding + curated landmark repository with exact GPS coordinates.
- **Output**: Real names, categories (`heritage`, `nature`, `viewpoint`, `bazaar`, `culinary`), coordinates (`lat`, `lon`), and neighborhood descriptions.
- **Downstream Coupling**: Feeds exact attraction names and coordinates directly into:
  - `TransportationRouteAgent` (for transit and route planning)
  - `PersonalizationRecommendationAgent` (for preference ranking and fit scores)
  - `ItineraryCompilerAgent` (for morning, afternoon, and evening daily activity scheduling)
  - Interactive Map (for Leaflet pin rendering)

### 4. Interactive Leaflet Map
- **Provider**: Leaflet 1.9 + OpenStreetMap standard tile server (`https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png`).
- **Markers**: Interactive popups with property/landmark names, categories, and coordinates.
- **Routing**: Shows geographic clustering of itinerary stops to minimize traveler transit time.

### 5. Weather Forecasts (`TravelSupportAgent`)
- **API Endpoint**: `https://api.open-meteo.com/v1/forecast`
- **Parameters**: `latitude`, `longitude`, `daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max`.
- **Horizon Policy**: If a trip's departure date is within 14 days, the real-time forecast is displayed. If the date is beyond 14 days, current conditions are displayed along with an explicit notification: *"Your trip departs in X days. Open-Meteo provides 14-day forecasts; check back 10 days before departure for precise daily predictions."*
- **Checklist Automation**: Pack weather recommendations (umbrella, SPF 50 sunscreen, warm layers) adapt dynamically to rain probability and forecast temperature extremes.

### 6. Foreign Exchange (`CurrencyProvider`)
- **Primary API**: `https://open.er-api.com/v6/latest/{base}`
- **Fallback**: Reference exchange rate table (USD, EUR, GBP, CAD, AUD, JPY, INR, CHF, SGD, BRL, MXN).
- **Precision**: All financial calculations use Python `Decimal` with `ROUND_HALF_UP` to prevent floating-point drift.

### 7. SaaS Billing & Subscriptions (`payments`)
- **Checkout**: Generates secure session identifiers and safe test URLs (`https://checkout.stripe.com/test?tier={tier}&user={user_id}`).
- **Webhooks**: Handles `checkout.session.completed`, maps subscription tiers (`pro`, `enterprise`), records payment amounts, and dispatches in-app confirmation notifications.

---

## 🔑 Required Credentials for Full Live Provider Activation

To enable live flight bookings, live Gemini LLM synthesis, or live Stripe credit card charges, add these variables to `backend/.env`:

```bash
# 1. Google Gemini AI (Itinerary & Concierge Synthesis)
# Obtain free API key: https://aistudio.google.com
GEMINI_API_KEY=your_gemini_api_key_here

# 2. Amadeus Self-Service (Live Flight Search & Live Hotel Offers)
# Obtain free developer test keys: https://developers.amadeus.com
AMADEUS_CLIENT_ID=your_amadeus_client_id_here
AMADEUS_CLIENT_SECRET=your_amadeus_client_secret_here
AMADEUS_BASE_URL=https://test.api.amadeus.com

# 3. Stripe Production Billing (Optional for live payments)
# Obtain keys from: https://dashboard.stripe.com
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

*Note: All other features (weather, destinations, interactive maps, multi-currency conversion, budget calculations, deterministic itinerary synthesis, account authentication, saved trips, and PDF/HTML exports) work immediately without any external API keys.*
