import asyncio
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

try:
    from fastapi import FastAPI, Header, HTTPException, Query, Response
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import HTMLResponse
except ImportError:  # pragma: no cover - runtime dependency is optional in this sandbox.
    FastAPI = None
    Header = None
    HTTPException = None
    Query = None
    Response = None
    HTMLResponse = None

from ..auth import authenticate_user, issue_token, register_user, verify_token
from ..core.types import TripSpec
from ..db import (
    add_conversation_message,
    check_user_trip_quota,
    create_notification,
    create_payment,
    create_trip,
    delete_trip,
    get_admin_stats,
    get_or_create_subscription,
    get_preferences,
    get_trip,
    get_user_by_id,
    list_conversations,
    list_notifications,
    list_trips,
    list_users,
    mark_notification_read,
    set_preference,
    update_subscription,
    update_trip,
)
from ..services.trip_service import TripService
from .n8n import router as n8n_router


def _require_token(authorization: str | None) -> dict[str, Any]:
    if authorization is None or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing or invalid authorization header")
    token = authorization.split(" ", 1)[1].strip()
    try:
        return verify_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="invalid or expired token") from exc


def _require_admin(authorization: str | None) -> dict[str, Any]:
    user = _require_token(authorization)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user


def _owned_trip(trip_id: str, user_id: str) -> dict[str, Any]:
    record = get_trip(trip_id)
    if record is None or record["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Trip not found")
    return record


async def _notify_n8n_trip_planned(trip_id: str, trip_spec: TripSpec, summary: str, user_id: str) -> None:
    n8n_url = os.getenv("N8N_WEBHOOK_URL")
    if not n8n_url:
        return
    secret = os.getenv("N8N_WEBHOOK_SECRET", "travelmind-n8n-secret")
    payload = {
        "correlation_id": f"corr-{uuid.uuid4()}",
        "action": "plan_travel",
        "trip_id": trip_id,
        "user_id": user_id,
        "destination": trip_spec.destination,
        "origin": trip_spec.origin,
        "departure_date": trip_spec.departure_date.isoformat() if trip_spec.departure_date else None,
        "return_date": trip_spec.return_date.isoformat() if trip_spec.return_date else None,
        "budget": trip_spec.budget,
        "currency": trip_spec.currency,
        "summary": summary,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.post(n8n_url, json=payload, headers={"X-N8N-Webhook-Secret": secret})
    except Exception:
        pass


async def _generate_concierge_reply(trip_data: dict[str, Any] | None, prompt: str) -> str:
    gemini_key = os.getenv("GEMINI_API_KEY")
    dest = (trip_data or {}).get("destination") or "your destination"
    origin = (trip_data or {}).get("origin") or "your origin"
    budget = (trip_data or {}).get("budget") or "Flexible"
    currency = (trip_data or {}).get("currency") or "USD"
    travelers = (trip_data or {}).get("travelers") or 1
    dates = f"{trip_data.get('departure_date', '')} to {trip_data.get('return_date', '')}" if trip_data else "Upcoming"

    # Attempt live Gemini 2.0 Flash call if configured
    if gemini_key:
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                sys_instruct = (
                    f"You are the TravelMind AI Concierge, an elite travel architect and local cultural specialist. "
                    f"The user has an active travel plan: Origin: {origin}, Destination: {dest}, Dates: {dates}, "
                    f"Travelers: {travelers}, Budget: {budget} {currency}. "
                    f"Answer the traveler's question with authoritative, helpful, concrete travel advice. "
                    f"Include specific named recommendations, local secrets, estimated prices, and practical tips. "
                    f"Format cleanly with markdown bullet points and bold highlights."
                )
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}"
                resp = await client.post(
                    url,
                    json={
                        "contents": [{"parts": [{"text": f"{sys_instruct}\n\nUser Question: {prompt}"}]}],
                        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 800}
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text")
                        if text:
                            return text.strip()
        except Exception:
            pass

    # Expert Contextual Local Travel Concierge Engine
    q = prompt.lower()
    dest_lower = dest.lower()

    if any(k in q for k in ["packing", "what to pack", "pack ", "clothes", "wear", "weather", "dress", "rain"]):
        if "goa" in dest_lower:
            return (
                f"### 🌴 Packing & Clothing Guide for Goa\n"
                f"- **Attire**: Breathable cottons, linen shirts, swimwear, UV-protect rashguards, and polarized sunglasses.\n"
                f"- **Footwear**: Sturdy flip-flops or water-resistant sandals for sandy beaches; comfortable sneakers for exploring forts.\n"
                f"- **Essentials**: High-SPF broad-spectrum sunscreen (coral-safe), DEET mosquito repellent (essential at dusk), and a waterproof pouch for phones/wallets during water sports.\n"
                f"- **Cultural Etiquette**: Modest attire covering shoulders and knees is required when entering churches like Basilica of Bom Jesus or Hindu temples in Ponda."
            )
        elif "jaipur" in dest_lower or "rajasthan" in dest_lower:
            return (
                f"### 👑 Packing & Attire Guide for Jaipur & Rajasthan\n"
                f"- **Attire**: Light breathable layers during daytime; carry a warm shawl, jacket, or pashmina for chilly desert evenings.\n"
                f"- **Footwear**: Cushioned walking shoes or sneakers with good grip — climbing the cobblestone ramps of Amber Fort and Nahargarh requires considerable walking.\n"
                f"- **Protection**: Wide-brimmed sun hat, sunglasses, hydrating lip balm, and skin moisturizer for the dry desert climate.\n"
                f"- **Cultural Etiquette**: Keep shoulders and legs covered when visiting sacred temples (Galtaji, Birla Mandir) and the inner royal courtyards of the City Palace."
            )
        elif "paris" in dest_lower or "europe" in dest_lower:
            return (
                f"### 🥐 Packing & Attire Guide for Paris\n"
                f"- **Attire**: Smart-casual chic — dark jeans, tailored trench coat or wool jacket, and stylish scarves (quintessential Parisian staple).\n"
                f"- **Footwear**: High-comfort broken-in walking shoes or stylish leather sneakers; cobblestone streets make thin heels impractical.\n"
                f"- **Weather Preparedness**: Compact wind-resistant umbrella and a light compact sweater for sudden seasonal showers.\n"
                f"- **Security**: Crossbody anti-theft bag with zipper closures to deter pickpockets in crowded metro stations and around the Eiffel Tower."
            )
        else:
            return (
                f"### 🧳 Packing Essentials for {dest}\n"
                f"- **Core Wardrobe**: Versatile mix-and-match layers adaptable to day-to-night temperature changes.\n"
                f"- **Footwear**: Well-cushioned walking shoes suited for 10,000+ daily steps across urban and historic sites.\n"
                f"- **Electronics**: Universal travel adapter, 10,000mAh power bank, and offline map downloads.\n"
                f"- **Health & Documents**: Compact medical kit, copies of IDs/visas, and local currency cards."
            )

    elif any(k in q for k in ["food", "eat", "dish", "restaurant", "cafe", "street food", "dinner", "lunch"]):
        if "goa" in dest_lower:
            return (
                f"### 🍤 Culinary & Dining Secrets in Goa\n"
                f"- **Must-Try Iconic Dishes**: Authentic Goan Fish Thali (Kingfish/Surmai), Prawn Balchão, Pork or Chicken Vindaloo, and traditional layered Bebinca dessert.\n"
                f"- **Iconic Seaside Shacks**: *Curlies* & *Shiva Valley* in South Anjuna for sunset bites; *Britto's* at Baga for baked crab and seafood platters.\n"
                f"- **Legendary Local Institutions**: *Ritz Classic* in Panjim (unmatched fish curry thali) and *Martin's Corner* in Betalbatim (frequented by celebrities).\n"
                f"- **Artisan Cafes in Assagao**: *Gunpowder* (Kerala-Goan fusion in a Portuguese courtyard) and *Babka* (exceptional coffee & pastries)."
            )
        elif "jaipur" in dest_lower:
            return (
                f"### 🥘 Royal & Street Food Delights in Jaipur\n"
                f"- **Street Food Legends**: Crispy, flaky **Pyaaz Kachori** at *Rawat Mishthan Bhandar* (Station Rd); creamy Lassi in earthen kulhads at *Lassiwala* (since 1944 on MI Road).\n"
                f"- **Royal Traditional Banquet**: Authentic **Dal Baati Churma** & **Gatte ki Sabzi** at *Laxmi Mishthan Bhandar (LMB)* in Johari Bazaar.\n"
                f"- **Non-Veg Specialty**: Spiced fiery **Laal Maas** (mutton slow-cooked in Mathania chillies) at *Handi* or *Niros* on MI Road.\n"
                f"- **Dinner Experience**: *Chokhi Dhani* cultural village for a traditional seated silver thali accompanied by folk acrobatics and puppet shows."
            )
        elif "mumbai" in dest_lower:
            return (
                f"### 🍛 Epicurean Guide to Mumbai\n"
                f"- **Street Food Heritage**: Piping hot **Vada Pav** outside Mithibai College / Dadar; butter-dripping **Pav Bhaji** at *Sardar Refreshments* (Tardeo) or Juhu Beach.\n"
                f"- **Legendary Seafood**: Butter Garlic Crab and Neer Dosa at *Trishna* (Kala Ghoda) or *Mahesh Lunch Home* (Fort).\n"
                f"- **Historic Irani Cafes**: Bun Maska, Keema Pav, and Irani Chai at *Cafe Leopold* or *Kyani & Co.* (since 1904).\n"
                f"- **Sweet Endings**: Malai Kulfi at *Chowpatty* and seasonal Alphonso Mango Cream at *Haji Ali Juice Centre*."
            )
        else:
            return (
                f"### 🍽️ Top Dining Recommendations for {dest}\n"
                f"- **Morning Heritage**: Begin at an acclaimed local cafe for fresh regional breakfast and specialty roasts.\n"
                f"- **Afternoon Street Food**: Explore vibrant central markets to taste traditional street snacks alongside local residents.\n"
                f"- **Evening Fine Dining**: Reserve an authentic regional bistro or rooftop dining venue showcasing signature heritage recipes."
            )

    elif any(k in q for k in ["hotel", "stay", "hostel", "cheap", "luxury", "resort", "accommodat", "backpacker", "villa"]):
        return (
            f"### 🏨 Accommodation Strategy for {dest}\n"
            f"- **Budget Backpacker / Hostels**: For social networking, solo travelers, and ultra-value rates (typically ₹900–₹1,800 or $18–$35/night), look for verified stays like *Zostel* or *The Hosteller*.\n"
            f"- **Mid-Range Boutique / Havelis**: Offering authentic regional charm, courtyards, and rooftop views (₹3,500–₹7,000 or $55–$95/night) within walking distance of central sights.\n"
            f"- **4-Star Premium Resorts**: Featuring swimming pools, multi-cuisine dining, and concierge services (₹8,500–₹16,000 or $110–$190/night).\n"
            f"- **5-Star Luxury & Heritage Palaces**: For once-in-a-lifetime heritage opulence, dedicated royal butlers, and world-class spas (₹22,000–₹50,000+ or $280–$600+/night).\n"
            f"- **Tip**: Check the *Hotels & Stays* tab to compare all curated options currently matched to your trip dates."
        )

    elif any(k in q for k in ["flight", "airline", "fare", "ticket", "airport"]):
        return (
            f"### ✈️ Air Travel Intelligence: {origin} &rarr; {dest}\n"
            f"- **Carrier Options**: Direct and convenient connections are operated by top carriers including IndiGo (6E), Air India (AI), and Vistara (UK).\n"
            f"- **Fare Tiering**: Economy Saver is ideal for light travelers with 7kg cabin + 15kg checked luggage; Economy Standard or Premium includes complimentary hot meals and priority baggage handling.\n"
            f"- **Booking Window**: Secure domestic promotional fares 3 to 4 weeks prior to departure for savings of up to 25–35%.\n"
            f"- **Airport Transfers**: We recommend using the official prepaid airport taxi booth or authorized ride-hail pickup zones to avoid unmarked street touts."
        )

    elif any(k in q for k in ["budget", "cost", "save", "money", "expensive", "cheaper"]):
        return (
            f"### 💰 Budget Optimization & Financial Guardrails\n"
            f"- **Current Trip Allocation**: Your budget of {budget} {currency} includes an automatic **12% contingency buffer** to protect against unexpected price swings.\n"
            f"- **Savings Opportunities**:\n"
            f"  1. *Stays*: Switching 2 nights to a boutique haveli or social hostel can free up 20–30% of your total accommodation spend.\n"
            f"  2. *Transit*: Utilize metro lines, prepaid rickshaws, or daily scooter rentals rather than ad-hoc private cab rentals.\n"
            f"  3. *Dining*: Mix renowned street-food icons and local thalis with occasional fine-dining evenings to enjoy premium flavor at half the cost.\n"
            f"- **Review**: Open the *Cost Breakdown* tab to inspect itemized allocations for flights, stays, food, and activities."
        )

    elif any(k in q for k in ["scam", "safe", "safety", "tip", "secret", "hidden gem"]):
        return (
            f"### 🛡️ Local Safety Tips & Insider Secrets for {dest}\n"
            f"- **Avoid Transportation Scams**: Always insist on metered fares or agree on price upfront before stepping into an auto-rickshaw; alternatively use Ola/Uber/GoaMiles.\n"
            f"- **Unregistered Guides**: Hire guides only from official ASI (Archaeological Survey of India) ticket counters inside monument gates wearing official ID badges.\n"
            f"- **Best Photography Windows**: Visit iconic forts and monuments early at 08:30 AM before tourist coaches arrive for crowd-free photography.\n"
            f"- **Drinking Water**: Always drink sealed bottled water or use filtered water stations at verified hotels; avoid unsealed crushed ice from roadside carts."
        )

    else:
        return (
            f"### 🗺️ TravelMind Concierge: Planning {origin} to {dest}\n"
            f"I have synchronized your {dates} travel parameters for **{travelers} traveler(s)** with a ceiling of **{budget} {currency}**.\n\n"
            f"- **Curated Landmarks**: Discovered top-rated iconic attractions across heritage forts, cultural spiritual sites, scenic viewpoints, and food streets.\n"
            f"- **Tiered Accommodations**: Curated verified properties from social backpacker hostels to 5-star royal heritage palaces.\n"
            f"- **Daily Pacing**: Morning, afternoon, and evening slots designed to minimize backtracking and optimize local dining.\n\n"
            f"*Feel free to ask me about local street food dishes, clothing and weather checklists, budget optimization, or hidden cultural gems!*"
        )


if FastAPI is not None:
    app = FastAPI(title="TravelMind AI API", version="0.2.0")
    cors_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000").split(",") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_origin_regex=r"^https://.*(\.vercel\.app|\.onrender\.com)$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    if n8n_router is not None:
        app.include_router(n8n_router)

    trip_service = TripService()

    @app.get("/health")
    @app.get("/api/v1/health")
    async def health() -> dict[str, Any]:
        return {"status": "ok", "service": "travelmind-ai", "version": "0.2.0"}

    # --- Authentication ---

    @app.post("/api/v1/auth/register")
    async def register(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            user = register_user(payload.get("email"), payload.get("password"), payload.get("full_name"), "traveler")
            token = issue_token(user)
            # Create a welcome notification
            create_notification(
                user["id"],
                type="system",
                title="Welcome to TravelMind AI",
                message="Your intelligent travel studio is ready. Start by planning your first journey!",
            )
            return {"user": {"id": user["id"], "email": user["email"], "full_name": user["full_name"], "role": user["role"]}, "token": token}
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/v1/auth/login")
    async def login(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            user = authenticate_user(payload.get("email"), payload.get("password"))
            token = issue_token(user)
            return {"user": user, "token": token}
        except ValueError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

    @app.get("/api/v1/auth/me")
    async def me(authorization: str | None = Header(default=None)) -> dict[str, Any]:
        user = _require_token(authorization)
        sub = get_or_create_subscription(user["sub"])
        quota = check_user_trip_quota(user["sub"])
        return {"user": user, "subscription": sub, "quota": quota}

    # --- Trips CRUD & Export ---

    @app.get("/api/v1/trips")
    async def list_user_trips(authorization: str | None = Header(default=None)) -> list[dict[str, Any]]:
        user = _require_token(authorization)
        return list_trips(user["sub"])

    @app.post("/api/v1/trips")
    @app.post("/api/v1/trips/plan")
    async def create_trip_route(payload: dict[str, Any], authorization: str | None = Header(default=None)) -> dict[str, Any]:
        user = _require_token(authorization)

        # Quota check
        quota = check_user_trip_quota(user["sub"])
        if not quota["allowed"]:
            raise HTTPException(
                status_code=403,
                detail=f"Plan limit reached ({quota['current_trips']}/{quota['max_trips']} trips). Please upgrade your subscription to plan more trips.",
            )

        trip_payload = dict(payload)
        if "start_date" in trip_payload and "departure_date" not in trip_payload:
            trip_payload["departure_date"] = trip_payload.pop("start_date")
        if "end_date" in trip_payload and "return_date" not in trip_payload:
            trip_payload["return_date"] = trip_payload.pop("end_date")
        if isinstance(trip_payload.get("preferences"), list):
            prefs_list = trip_payload.pop("preferences")
            if "interests" not in trip_payload:
                trip_payload["interests"] = prefs_list
            trip_payload["preferences"] = {"interests": prefs_list}

        try:
            trip = TripSpec.from_dict(trip_payload)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        plan = await trip_service.plan_trip_async(trip)
        if isinstance(trip.preferences, dict):
            preferences = dict(trip.preferences)
        elif isinstance(trip.preferences, list):
            preferences = {"interests": trip.preferences}
        else:
            preferences = {}
        if trip.interests:
            preferences["interests"] = trip.interests

        saved = create_trip(
            user["sub"],
            {
                "origin": trip.origin,
                "destination": trip.destination,
                "departure_date": trip.departure_date.isoformat() if trip.departure_date else None,
                "return_date": trip.return_date.isoformat() if trip.return_date else None,
                "duration_days": trip.duration_days,
                "travelers": trip.travelers,
                "budget": trip.budget,
                "currency": trip.currency,
                "status": "draft",
                "summary": plan.summary,
                "preferences": preferences,
                "plan_results": plan.results,
            },
        )

        # Non-blocking async event dispatch to n8n webhook listener if running
        try:
            asyncio.create_task(_notify_n8n_trip_planned(saved["id"], trip, plan.summary, user["sub"]))
        except Exception:
            pass

        return {
            **saved,
            "trip_id": saved["id"],
            "missing_fields": plan.missing_fields,
            "itinerary": plan.results.get("itinerary", {}).get("days", []),
            "agent_results": plan.results,
        }

    @app.get("/api/v1/trips/{trip_id}")
    async def get_trip_route(trip_id: str, authorization: str | None = Header(default=None)) -> dict[str, Any]:
        user = _require_token(authorization)
        return _owned_trip(trip_id, user["sub"])

    @app.patch("/api/v1/trips/{trip_id}")
    async def update_trip_route(trip_id: str, payload: dict[str, Any], authorization: str | None = Header(default=None)) -> dict[str, Any]:
        user = _require_token(authorization)
        existing = _owned_trip(trip_id, user["sub"])
        if set(payload) & {"user_id", "id", "plan_results"}:
            raise HTTPException(status_code=422, detail="user_id, id, and plan_results cannot be updated directly")
        updates = dict(payload)
        interests = updates.pop("interests", None)
        if "preferences" in updates:
            updates["preferences"] = {**existing["preferences"], **updates["preferences"]}
        if interests is not None:
            updates["preferences"] = {**existing["preferences"], **updates.get("preferences", {}), "interests": interests}
        if set(updates) & {"origin", "destination", "departure_date", "return_date", "duration_days", "travelers", "budget", "currency", "preferences"}:
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
            planning_payload["interests"] = planning_payload["preferences"].get("interests", [])
            try:
                updated_spec = TripSpec.from_dict(planning_payload)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            plan = await trip_service.plan_trip_async(updated_spec)
            updates["summary"] = plan.summary
            updates["plan_results"] = plan.results
        try:
            updated = update_trip(trip_id, updates)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return updated or {}

    @app.delete("/api/v1/trips/{trip_id}")
    async def delete_trip_route(trip_id: str, authorization: str | None = Header(default=None)) -> dict[str, Any]:
        user = _require_token(authorization)
        _owned_trip(trip_id, user["sub"])
        deleted = delete_trip(trip_id)
        return {"status": "deleted", "id": trip_id, "success": deleted}

    @app.get("/api/v1/trips/{trip_id}/export")
    async def export_trip_route(
        trip_id: str,
        export_format: str = Query(default="json", alias="format"),
        authorization: str | None = Header(default=None),
    ):
        """Exports a trip itinerary as formatted HTML, JSON, or printable document."""
        user = _require_token(authorization)
        trip = _owned_trip(trip_id, user["sub"])

        if export_format == "html":
            itinerary = trip.get("plan_results", {}).get("itinerary", {})
            days_html = ""
            for d in itinerary.get("days", []):
                act_items = "".join(f"<li>{a}</li>" for a in d.get("activities", []))
                days_html += f"""
                <div style="margin-bottom: 24px; padding: 16px; border: 1px solid #e2e8f0; border-radius: 8px;">
                    <h3 style="color: #0f172a; margin-top: 0;">Day {d.get('day')}: {d.get('title', '')}</h3>
                    <ul style="color: #475569; line-height: 1.6;">{act_items}</ul>
                </div>
                """
            budget = trip.get("plan_results", {}).get("budget_intelligence", {}).get("data", {})
            budget_html = f"Total Estimated: <strong>{budget.get('total', trip.get('budget'))} {trip.get('currency')}</strong>"

            html = f"""<!DOCTYPE html>
            <html>
            <head><meta charset="utf-8"><title>{trip.get('origin')} to {trip.get('destination')} Itinerary</title>
            <style>body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; }}</style>
            </head>
            <body>
                <header style="border-bottom: 2px solid #0f172a; padding-bottom: 16px; margin-bottom: 24px;">
                    <h1 style="margin: 0; color: #0f172a;">TravelMind AI Itinerary</h1>
                    <p style="color: #64748b; margin: 4px 0 0;">{trip.get('origin')} &rarr; {trip.get('destination')} | {trip.get('departure_date')} to {trip.get('return_date') or 'Flexible'}</p>
                    <p>{budget_html}</p>
                </header>
                {days_html}
                <footer style="margin-top: 32px; font-size: 12px; color: #94a3b8; text-align: center;">
                    Generated by TravelMind AI on {datetime.now(timezone.utc).strftime('%Y-%m-%d')}
                </footer>
            </body></html>"""
            return HTMLResponse(content=html)

        itinerary = trip.get("plan_results", {}).get("itinerary", {})
        return {
            "trip": trip,
            "itinerary": itinerary.get("days", []),
            "plan_results": trip.get("plan_results", {}),
            "summary": trip.get("summary", ""),
            "destination": trip.get("destination", ""),
            "origin": trip.get("origin", ""),
            "status": trip.get("status", "draft"),
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }

    # --- AI Travel Assistant & Chat ---

    @app.get("/api/v1/conversations")
    async def get_conversations(
        trip_id: str | None = None,
        authorization: str | None = Header(default=None),
    ) -> list[dict[str, Any]]:
        user = _require_token(authorization)
        return list_conversations(user["sub"], trip_id)

    @app.post("/api/v1/conversations")
    async def post_conversation_message(
        payload: dict[str, Any],
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        user = _require_token(authorization)
        trip_id = payload.get("trip_id")
        content = payload.get("content", "").strip()
        if not content:
            raise HTTPException(status_code=422, detail="Message content cannot be empty")

        # Save user message
        add_conversation_message(user["sub"], trip_id, "user", content)

        # Retrieve active trip context if available
        trip_data = None
        if trip_id:
            try:
                trip_data = get_trip(trip_id)
            except Exception:
                trip_data = None

        # Generate intelligent assistant response
        reply = await _generate_concierge_reply(trip_data, content)

        # Save assistant message
        bot_msg = add_conversation_message(user["sub"], trip_id, "assistant", reply)
        return bot_msg

    # --- User Preferences ---

    @app.get("/api/v1/preferences")
    async def user_preferences(authorization: str | None = Header(default=None)) -> dict[str, Any]:
        user = _require_token(authorization)
        return get_preferences(user["sub"])

    @app.put("/api/v1/preferences")
    async def set_user_preference(
        payload: dict[str, Any],
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        user = _require_token(authorization)
        for k, v in payload.items():
            set_preference(user["sub"], k, v)
        return get_preferences(user["sub"])

    # --- Notifications ---

    @app.get("/api/v1/notifications")
    async def user_notifications(authorization: str | None = Header(default=None)) -> list[dict[str, Any]]:
        user = _require_token(authorization)
        return list_notifications(user["sub"])

    @app.patch("/api/v1/notifications/{notif_id}/read")
    async def mark_notif_read(
        notif_id: str,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        _require_token(authorization)
        success = mark_notification_read(notif_id)
        return {"id": notif_id, "status": "read", "success": success}

    # --- Subscriptions & Billing ---

    @app.get("/api/v1/subscriptions/tiers")
    async def subscription_tiers() -> list[dict[str, Any]]:
        return [
            {
                "tier": "free",
                "name": "Traveler Free",
                "price_usd": 0.0,
                "interval": "forever",
                "features": ["3 saved trips", "Standard itinerary synthesis", "Open weather & currency sync", "Manual trip export"],
            },
            {
                "tier": "pro",
                "name": "TravelMind Pro",
                "price_usd": 14.99,
                "interval": "month",
                "popular": True,
                "features": ["Unlimited saved trips", "Amadeus live flight integration", "Gemini 2.0 Flash AI customization", "Full PDF & HTML export", "Real-time trip modification"],
            },
            {
                "tier": "enterprise",
                "name": "Concierge Elite",
                "price_usd": 49.99,
                "interval": "month",
                "features": ["Everything in Pro", "WhatsApp personal AI concierge", "n8n automated notification workflows", "Priority live provider queue", "Dedicated support"],
            },
        ]

    @app.get("/api/v1/subscriptions/current")
    @app.get("/api/v1/subscription/me")
    async def current_subscription(authorization: str | None = Header(default=None)) -> dict[str, Any]:
        user = _require_token(authorization)
        sub = get_or_create_subscription(user["sub"])
        quota = check_user_trip_quota(user["sub"])
        res = dict(sub)
        res["trips_remaining"] = quota.get("remaining_trips", 0)
        res["quota"] = quota
        return res

    @app.post("/api/v1/subscriptions/upgrade")
    async def upgrade_subscription(
        payload: dict[str, Any],
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        user = _require_token(authorization)
        new_tier = payload.get("tier", "pro")
        if new_tier not in {"free", "pro", "enterprise"}:
            raise HTTPException(status_code=400, detail="Invalid subscription tier")

        updated = update_subscription(user["sub"], new_tier)
        # Record payment if upgrading to paid tier
        if new_tier != "free":
            price = 14.99 if new_tier == "pro" else 49.99
            create_payment(user["sub"], amount=price, currency="USD", provider_payment_id=f"pay-{uuid.uuid4()}")
            create_notification(
                user["sub"],
                type="system",
                title=f"Upgraded to {new_tier.title()} Plan",
                message=f"Thank you for upgrading! You now have full access to {new_tier.title()} capabilities.",
            )
        return updated

    @app.post("/api/v1/payments/checkout")
    async def create_checkout_session(
        payload: dict[str, Any],
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        user = _require_token(authorization)
        tier = payload.get("tier", "pro")
        return {
            "session_id": f"cs_test_{uuid.uuid4()}",
            "checkout_url": f"https://checkout.stripe.com/test?tier={tier}&user={user['sub']}",
            "status": "ready",
        }

    @app.post("/api/v1/payments/webhook")
    async def stripe_webhook(payload: dict[str, Any]) -> dict[str, Any]:
        """Stripe webhook receiver."""
        event_type = payload.get("type", "checkout.session.completed")
        user_id = payload.get("data", {}).get("object", {}).get("client_reference_id")
        if user_id:
            update_subscription(user_id, "pro")
            create_payment(user_id, amount=14.99, currency="USD")
        return {"received": True, "event": event_type}

    # --- Admin Dashboard ---

    @app.get("/api/v1/admin/stats")
    async def admin_stats(authorization: str | None = Header(default=None)) -> dict[str, Any]:
        _require_admin(authorization)
        return get_admin_stats()

    @app.get("/api/v1/admin/users")
    async def admin_list_users(authorization: str | None = Header(default=None)) -> list[dict[str, Any]]:
        _require_admin(authorization)
        return list_users()

else:
    app = None


def create_app() -> Any:
    if app is None:
        class _FallbackApp:
            def __getattr__(self, name):
                raise RuntimeError("FastAPI is not installed in this environment.")

        return _FallbackApp()
    return app
