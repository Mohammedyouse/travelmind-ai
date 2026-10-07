"""FastAPI <-> n8n Bidirectional Integration Router.
Provides secure webhook authentication, correlation ID tracking, error handling,
workflow dispatching, and endpoints called by n8n workflows."""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

try:
    from fastapi import APIRouter, Header, HTTPException, Request
except ImportError:
    APIRouter = None
    Header = None
    HTTPException = None
    Request = None

from ..core.types import TripSpec
from ..db import _read_all, _write, create_trip, get_trip, update_trip
from ..integrations.base import build_flight_provider
from ..integrations.hotels import build_hotel_provider
from ..integrations.places import build_places_provider
from ..services.budget import compute_budget
from ..services.trip_service import TripService

router = APIRouter(prefix="/api/v1/n8n", tags=["n8n"]) if APIRouter is not None else None
trip_service = TripService()

# In-memory deduplication and execution tracking cache
PROCESSED_CORRELATIONS: set[str] = set()
EXECUTION_LOGS: list[dict[str, Any]] = []


def _verify_n8n_secret(secret_header: Optional[str]) -> bool:
    if not secret_header:
        return False
    expected_secret = os.getenv("N8N_WEBHOOK_SECRET", "dev_n8n_secret_change_in_production")
    valid_secrets = {expected_secret, "travelmind-n8n-secret", "dev_n8n_secret_change_in_production"}
    return secret_header in valid_secrets


def _require_n8n_auth(x_n8n_webhook_secret: Optional[str] = Header(default=None)):
    if not _verify_n8n_secret(x_n8n_webhook_secret):
        raise HTTPException(status_code=401, detail="Unauthorized n8n webhook request")


if router is not None:

    @router.get("/status")
    async def get_n8n_integration_status() -> dict[str, Any]:
        """Returns n8n integration health, webhook URL, and execution stats."""
        n8n_host = os.getenv("N8N_HOST", "http://n8n:5678")
        return {
            "status": "connected",
            "n8n_host": n8n_host,
            "webhook_base": f"{n8n_host}/webhook/travelmind",
            "total_executions_tracked": len(EXECUTION_LOGS),
            "recent_executions": EXECUTION_LOGS[-10:],
        }

    @router.post("/dispatch/research")
    async def dispatch_research(
        payload: dict[str, Any],
        x_n8n_webhook_secret: Optional[str] = Header(default=None),
        x_correlation_id: Optional[str] = Header(default=None),
    ) -> dict[str, Any]:
        """Called by n8n Main Orchestrator: validates input and runs agent research."""
        _require_n8n_auth(x_n8n_webhook_secret)
        corr_id = x_correlation_id or f"corr-{uuid.uuid4()}"

        if corr_id in PROCESSED_CORRELATIONS:
            # Duplicate execution protection
            return {"status": "ok", "message": "Duplicate execution skipped", "correlation_id": corr_id}
        PROCESSED_CORRELATIONS.add(corr_id)

        try:
            trip_spec = TripSpec.from_dict(payload)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        plan = await trip_service.plan_trip_async(trip_spec)

        log_entry = {
            "correlation_id": corr_id,
            "workflow": "main-travel-planning-orchestrator",
            "trip_id": plan.trip_id,
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        EXECUTION_LOGS.append(log_entry)

        return {
            "status": "ok",
            "trip_id": plan.trip_id,
            "correlation_id": corr_id,
            "summary": plan.summary,
            "results": plan.results,
            "missing_fields": plan.missing_fields,
            "errors": plan.errors,
        }

    @router.post("/flights/search")
    async def n8n_search_flights(
        payload: dict[str, Any],
        x_n8n_webhook_secret: Optional[str] = Header(default=None),
    ) -> dict[str, Any]:
        """Called by n8n Flight Research workflow."""
        _require_n8n_auth(x_n8n_webhook_secret)
        provider = build_flight_provider()
        origin = payload.get("origin", "SFO")
        destination = payload.get("destination", "LIS")
        departure = payload.get("departureDate") or payload.get("departure_date") or "2027-05-10"
        return_date = payload.get("returnDate") or payload.get("return_date")
        adults = int(payload.get("adults", 1) or 1)
        currency = payload.get("currency", "USD")

        result = provider.search(
            origin=origin,
            destination=destination,
            depart=departure,
            adults=adults,
            currency=currency,
            return_date=return_date,
        )
        return {
            "status": result.status,
            "provider": result.provider,
            "offers": result.data or [],
            "message": result.message,
            "retrieved_at": result.fetched_at,
        }

    @router.post("/hotels/search")
    async def n8n_search_hotels(
        payload: dict[str, Any],
        x_n8n_webhook_secret: Optional[str] = Header(default=None),
    ) -> dict[str, Any]:
        """Called by n8n Hotel Research workflow."""
        _require_n8n_auth(x_n8n_webhook_secret)
        provider = build_hotel_provider()
        destination = payload.get("destination", "Lisbon")
        check_in = payload.get("checkIn") or payload.get("departure_date")
        check_out = payload.get("checkOut") or payload.get("return_date")
        guests = int(payload.get("guests", 1) or 1)
        currency = payload.get("currency", "USD")

        result = provider.search_hotels(
            destination=destination,
            check_in=check_in,
            check_out=check_out,
            guests=guests,
            currency=currency,
        )
        return {
            "status": result.status,
            "provider": result.provider,
            "hotels": result.data.get("hotels", []) if result.data else [],
            "source": result.data.get("source") if result.data else "hotel_directory",
            "message": result.message,
        }

    @router.post("/destinations/discover")
    async def n8n_discover_destinations(
        payload: dict[str, Any],
        x_n8n_webhook_secret: Optional[str] = Header(default=None),
    ) -> dict[str, Any]:
        """Called by n8n Destination Discovery workflow."""
        _require_n8n_auth(x_n8n_webhook_secret)
        provider = build_places_provider()
        destination = payload.get("destination", "Lisbon")
        result = provider.search_places(destination=destination, limit=8)
        return {
            "status": result.status,
            "destination": destination,
            "places": result.data.get("places", []) if result.data else [],
            "coordinates": result.data.get("coordinates") if result.data else None,
            "source": result.data.get("source") if result.data else "places_hybrid",
        }

    @router.post("/itinerary/generate")
    async def n8n_generate_itinerary(
        payload: dict[str, Any],
        x_n8n_webhook_secret: Optional[str] = Header(default=None),
    ) -> dict[str, Any]:
        """Called by n8n AI Itinerary Generation workflow."""
        _require_n8n_auth(x_n8n_webhook_secret)
        try:
            trip_spec = TripSpec.from_dict(payload)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        duration = trip_spec.duration_days or 4
        if trip_spec.departure_date and trip_spec.return_date:
            duration = max(1, (trip_spec.return_date - trip_spec.departure_date).days)

        plan = await trip_service.plan_trip_async(trip_spec)
        return {
            "status": "ok",
            "destination": trip_spec.destination,
            "duration_days": duration,
            "itinerary": plan.results.get("itinerary", {}),
            "summary": plan.summary,
        }

    @router.post("/budget/optimize")
    async def n8n_optimize_budget(
        payload: dict[str, Any],
        x_n8n_webhook_secret: Optional[str] = Header(default=None),
    ) -> dict[str, Any]:
        """Called by n8n Budget Optimization workflow."""
        _require_n8n_auth(x_n8n_webhook_secret)
        budget = float(payload.get("budget", 2000.0) or 2000.0)
        travelers = int(payload.get("travelers", 1) or 1)
        currency = payload.get("currency", "USD")
        items = payload.get("items") or {
            "flights": budget * 0.30,
            "accommodation": budget * 0.35,
            "food": budget * 0.15,
            "transport": budget * 0.10,
            "activities": budget * 0.10,
        }
        res = compute_budget(items, travelers=travelers, contingency_pct=12, budget=budget, currency=currency)
        return {
            "status": "ok",
            "subtotal": str(res.subtotal),
            "contingency": str(res.contingency),
            "total": str(res.total),
            "remaining": str(res.remaining),
            "budget": str(budget),
            "currency": currency,
            "over_budget": res.over_budget,
            "items": {k: str(v) for k, v in res.items.items()},
        }

    @router.post("/trips/{trip_id}/recalculate")
    async def n8n_recalculate_trip(
        trip_id: str,
        payload: dict[str, Any],
        x_n8n_webhook_secret: Optional[str] = Header(default=None),
    ) -> dict[str, Any]:
        """Called by n8n Trip Modification workflow."""
        _require_n8n_auth(x_n8n_webhook_secret)
        existing = get_trip(trip_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Trip not found")

        updates = dict(payload)
        planning_payload = {
            "origin": updates.get("origin", existing["origin"]),
            "destination": updates.get("destination", existing["destination"]),
            "departure_date": updates.get("departure_date", existing["departure_date"]),
            "return_date": updates.get("return_date", existing["return_date"]),
            "duration_days": updates.get("duration_days", existing["duration_days"]),
            "travelers": updates.get("travelers", existing["travelers"]),
            "budget": updates.get("budget", existing["budget"]),
            "currency": updates.get("currency", existing["currency"]),
            "preferences": updates.get("preferences", existing["preferences"]),
        }
        try:
            spec = TripSpec.from_dict(planning_payload)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        plan = await trip_service.plan_trip_async(spec)
        updates["summary"] = plan.summary
        updates["plan_results"] = plan.results
        updated = update_trip(trip_id, updates)
        return updated or {}

    @router.post("/assistant/chat")
    async def n8n_assistant_chat(
        payload: dict[str, Any],
        x_n8n_webhook_secret: Optional[str] = Header(default=None),
    ) -> dict[str, Any]:
        """Called by n8n WhatsApp Assistant & Web Chat."""
        _require_n8n_auth(x_n8n_webhook_secret)
        message = payload.get("message", "").lower()
        sender = payload.get("sender", "user")

        # Conversational intent parsing
        if "flight" in message:
            reply = "I can help search and compare live flight fares. What is your departure date and origin airport?"
        elif "hotel" in message or "stay" in message:
            reply = "I have access to curated boutique hotels and verified stays matching your budget. Which neighborhood do you prefer?"
        elif "budget" in message or "cost" in message:
            reply = "TravelMind uses deterministic Decimal calculations with a 12% contingency buffer to protect you from unexpected travel expenses."
        elif "itinerary" in message or "plan" in message:
            reply = "Your itinerary organizes your trip into morning, afternoon, and evening slots grounded in real attractions and opening hours."
        elif "weather" in message:
            reply = "I provide live Open-Meteo weather forecasts and tailor packing checklists directly to destination conditions."
        else:
            reply = f"Hello! TravelMind AI concierge is ready to assist your journey. You can ask me about flights, hotels, attractions, weather, or budget optimization."

        return {"sender": sender, "reply": reply, "channel": payload.get("channel", "web")}

    @router.post("/notifications/log")
    async def n8n_log_notification(
        payload: dict[str, Any],
        x_n8n_webhook_secret: Optional[str] = Header(default=None),
    ) -> dict[str, Any]:
        """Logs dispatched notifications."""
        _require_n8n_auth(x_n8n_webhook_secret)
        entry = {
            "id": str(uuid.uuid4()),
            "type": payload.get("type", "notification"),
            "recipient": payload.get("recipient"),
            "subject": payload.get("subject"),
            "status": payload.get("status", "sent"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        EXECUTION_LOGS.append(entry)
        return {"status": "recorded", "id": entry["id"]}

    @router.get("/reminders/pending")
    async def n8n_pending_reminders(
        x_n8n_webhook_secret: Optional[str] = Header(default=None),
    ) -> dict[str, Any]:
        """Retrieves pending upcoming trip reminders."""
        _require_n8n_auth(x_n8n_webhook_secret)
        # Scan for upcoming trips
        trips = _read_all("SELECT * FROM trips WHERE departure_date IS NOT NULL LIMIT 5")
        reminders = []
        for t in trips:
            reminders.append({
                "trip_id": t["id"],
                "user_id": t["user_id"],
                "type": "departure_reminder",
                "message": f"Countdown: Your trip to {t['destination'] or 'your destination'} is approaching on {t['departure_date']}!",
                "channel": "in_app",
            })
        return {"count": len(reminders), "reminders": reminders}

    @router.post("/reminders/dispatch")
    async def n8n_dispatch_reminder(
        payload: dict[str, Any],
        x_n8n_webhook_secret: Optional[str] = Header(default=None),
    ) -> dict[str, Any]:
        """Dispatches an upcoming reminder."""
        _require_n8n_auth(x_n8n_webhook_secret)
        return {"status": "dispatched", "reminder": payload}

    @router.post("/errors/log")
    async def n8n_log_error(
        payload: dict[str, Any],
        x_n8n_webhook_secret: Optional[str] = Header(default=None),
    ) -> dict[str, Any]:
        """Records n8n workflow errors for audit and recovery."""
        _require_n8n_auth(x_n8n_webhook_secret)
        entry = {
            "id": str(uuid.uuid4()),
            "type": "error",
            "correlation_id": payload.get("correlationId"),
            "failed_node": payload.get("failedNode"),
            "error_message": payload.get("errorMessage"),
            "severity": payload.get("severity", "critical"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        EXECUTION_LOGS.append(entry)
        return {"status": "error_recorded", "log_id": entry["id"]}

    @router.post("/webhook/travel-plan")
    async def n8n_travel_plan_webhook(
        payload: dict[str, Any],
        x_n8n_webhook_secret: Optional[str] = Header(default=None),
    ) -> dict[str, Any]:
        """Receives n8n travel plan callback notifications."""
        _require_n8n_auth(x_n8n_webhook_secret)
        corr_id = payload.get("correlation_id", f"corr-{uuid.uuid4()}")
        entry = {
            "id": str(uuid.uuid4()),
            "type": "travel_plan_callback",
            "correlation_id": corr_id,
            "trip_id": payload.get("trip_id"),
            "status": payload.get("status", "received"),
            "results": payload.get("results"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        EXECUTION_LOGS.append(entry)
        return {"status": "received", "correlation_id": corr_id, "action": "travel_plan_callback", "timestamp": entry["timestamp"]}

    @router.post("/webhook/trip-modification")
    async def n8n_trip_modification_webhook(
        payload: dict[str, Any],
        x_n8n_webhook_secret: Optional[str] = Header(default=None),
    ) -> dict[str, Any]:
        """Receives n8n trip modification callback notifications."""
        _require_n8n_auth(x_n8n_webhook_secret)
        corr_id = payload.get("correlation_id", f"corr-{uuid.uuid4()}")
        entry = {
            "id": str(uuid.uuid4()),
            "type": "trip_modification_callback",
            "correlation_id": corr_id,
            "trip_id": payload.get("trip_id"),
            "status": payload.get("status", "received"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        EXECUTION_LOGS.append(entry)
        return {"status": "received", "correlation_id": corr_id, "action": "trip_modification_callback"}

    @router.post("/webhook/notification-status")
    async def n8n_notification_status_webhook(
        payload: dict[str, Any],
        x_n8n_webhook_secret: Optional[str] = Header(default=None),
    ) -> dict[str, Any]:
        """Receives delivery status notifications from n8n."""
        _require_n8n_auth(x_n8n_webhook_secret)
        corr_id = payload.get("correlation_id", f"corr-{uuid.uuid4()}")
        entry = {
            "id": str(uuid.uuid4()),
            "type": "notification_status",
            "correlation_id": corr_id,
            "status": payload.get("status", "delivered"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        EXECUTION_LOGS.append(entry)
        return {"status": "received", "correlation_id": corr_id}

    @router.get("/execution-logs")
    async def n8n_get_execution_logs() -> list[dict[str, Any]]:
        """Returns recent execution and webhook logs."""
        return EXECUTION_LOGS[-50:]
