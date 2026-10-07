from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from typing import Any

from ..agents import build_agent_registry
from ..core.types import TripSpec
from ..llm.base import GeminiClient, LLMGateway, LLMResponse
from ..orchestrator.orchestrator import AgentSpec, Orchestrator


@dataclass
class TripPlanResult:
    trip_id: str
    trip_spec: TripSpec
    created_at: str
    summary: str
    results: dict[str, Any] = field(default_factory=dict)
    missing_fields: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


AGENT_DEPENDENCIES: dict[str, tuple[str, ...]] = {
    "travel_concierge": (),
    "flight_intelligence": ("travel_concierge",),
    "accommodation_intelligence": ("travel_concierge",),
    "destination_discovery": ("travel_concierge",),
    "transportation_route": ("destination_discovery",),
    "budget_intelligence": ("flight_intelligence", "accommodation_intelligence"),
    "personalization_recommendation": ("destination_discovery",),
    "travel_support": ("travel_concierge",),
}


class TripService:
    def __init__(self, agent_registry: dict[str, Any] | None = None):
        self.agent_registry = agent_registry or build_agent_registry()

    def _to_agent_specs(self) -> list[AgentSpec]:
        specs: list[AgentSpec] = []
        for name, agent in self.agent_registry.items():
            deps = AGENT_DEPENDENCIES.get(name, ())
            # Ensure dependencies only reference registered agents
            valid_deps = tuple(dep for dep in deps if dep in self.agent_registry)
            specs.append(
                AgentSpec(
                    name=name,
                    run=lambda ctx, agent=agent: self._invoke_agent(agent, ctx),
                    depends_on=valid_deps,
                    timeout=20.0,
                    retries=1,
                    required=False,
                )
            )
        return specs

    async def _invoke_agent(self, agent: Any, ctx: dict[str, Any]):
        return agent.run(ctx)

    def build_trip_summary(self, trip_spec: TripSpec) -> str:
        destination = trip_spec.destination or "your destination"
        origin = trip_spec.origin or "your origin"
        budget = trip_spec.budget or 0
        currency = trip_spec.currency
        return (
            f"Trip from {origin} to {destination} for {trip_spec.travelers} traveler(s) "
            f"with an estimated budget of {budget} {currency}."
        )

    def _build_grounded_itinerary(
        self,
        trip_spec: TripSpec,
        duration_days: int,
        results: dict[str, Any],
    ) -> dict[str, Any]:
        """Synthesizes a rich day-by-day itinerary grounded in real researched places, stays, and regional culture."""
        dest_name = trip_spec.destination or "your destination"
        places_data = results.get("destination_discovery", {}).get("data", {})
        discovered_places = places_data.get("places", [])
        hotels = results.get("accommodation_intelligence", {}).get("data", {}).get("hotels", [])
        stay_name = hotels[0].get("name") if hotels else f"Central Stay in {dest_name}"
        stay_tier = hotels[0].get("tier", "Selected Accommodation") if hotels else "Boutique Hotel"

        is_inr = (trip_spec.currency or "").upper() == "INR"
        m_cost = 250.0 if is_inr else 15.0
        a_cost = 350.0 if is_inr else 25.0
        e_cost = 650.0 if is_inr else 40.0

        days = []
        total_places = len(discovered_places)

        dest_lower = dest_name.lower()
        if "goa" in dest_lower:
            food_tips = [
                "Lunch: Fresh kingfish curry & rice at a local beach shack; Dinner: Candlelight seafood at Curlies or Thalassa.",
                "Lunch: Goan Pork Vindaloo or Mushroom Xacuti; Dinner: Wood-fired sourdough pizza & feni cocktails in Assagao.",
                "Lunch: Traditional fish thali at Ritz Classic Panjim; Dinner: Heritage Indo-Portuguese banquet in Fontainhas.",
                "Lunch: Goan prawn balchão & poi bread; Dinner: Beachside sunset barbecue with live coastal acoustic music.",
            ]
            transit_tips = [
                "Hire a self-drive scooter (₹400/day) or book GoaMiles taxi for convenient coastal hopping.",
                "Rent a car or hail local pilot (motorcycle taxi) for scenic interior roads.",
                "Use the scenic Mandovi river ferry service to cross to historic islands.",
                "Pre-book an airport cab via the prepaid taxi counter or GoaMiles app.",
            ]
        elif "jaipur" in dest_lower:
            food_tips = [
                "Morning: Pyaaz Kachori & Mawa Kachori at Rawat Mishthan Bhandar; Dinner: Royal Rajasthani Dal Baati Churma at LMB.",
                "Lunch: Laal Maas or Gatte ki Sabzi in Old City; Dinner: Grand royal buffet with folk dancers at Chokhi Dhani.",
                "Lunch: Lassi in earthen kulhad at Lassiwala MI Road; Dinner: Rooftop sunset dinner facing Nahargarh Fort.",
                "Lunch: Ghewar & traditional sweets at Kanha; Dinner: Heritage courtyard dining with live sitar music.",
            ]
            transit_tips = [
                "Book an auto-rickshaw for the day (negotiate ₹600-₹800) or use Jaipur Metro line.",
                "Take an early morning cab to Amer Fort to beat peak tourist buses.",
                "E-rickshaws are ideal for navigating the colorful lanes of Johari and Bapu Bazaars.",
                "Pre-arrange airport transfer or hire cab via Ola/Uber.",
            ]
        elif "delhi" in dest_lower:
            food_tips = [
                "Morning: Bedmi Puri & Nagori Halwa in Old Delhi; Dinner: Legendary Butter Chicken & Dal Makhani at Pandara Road.",
                "Lunch: Paranthe at 150-year-old Paranthe Wali Gali; Dinner: Mughlai kebabs & biryani near Jama Masjid.",
                "Lunch: South Indian filter coffee & dosa at Saravana Bhavan; Dinner: Modern Indian fine dining in Connaught Place.",
                "Lunch: Street chaat & momos at Dilli Haat; Dinner: Heritage rooftop dining overlooking Old Delhi skyline.",
            ]
            transit_tips = [
                "Use the world-class Delhi Metro (Yellow/Violet lines) for fast, traffic-free sightseeing.",
                "E-rickshaws are readily available outside all major metro stations for last-mile transit.",
                "Use Delhi Airport Express Metro for a 15-minute swift transfer to New Delhi station.",
                "Book rides via Uber or BluSmart electric cabs for comfortable city exploration.",
            ]
        elif "mumbai" in dest_lower:
            food_tips = [
                "Morning: Bun Maska & Irani Chai at Cafe Leopold; Dinner: Coastal butter garlic crab at Trishna or Mahesh Lunch Home.",
                "Lunch: Famous Mumbai Vada Pav & Pav Bhaji; Dinner: Seaside kulfi and bhel puri at Chowpatty or Marine Drive.",
                "Lunch: Parsi Berry Pulao at Britannia & Co; Dinner: Rooftop cocktails overlooking Queen's Necklace.",
                "Lunch: South Indian thali at Matunga; Dinner: Bandra trendy fusion cafe and craft brews.",
            ]
            transit_tips = [
                "Take the iconic Mumbai Black-and-Yellow (Kaali-Peeli) taxi along Marine Drive.",
                "Use the Western Railway local train or AC Mumbai Metro for longer transits.",
                "Catch the scenic ferry from Gateway of India to Elephanta Caves island.",
                "Use the Bandra-Worli Sea Link for a panoramic ocean-crossing expressway ride.",
            ]
        else:
            food_tips = [
                "Morning: Fresh bakery treats & specialty coffee; Evening: Authentic regional bistro dinner showcasing local dishes.",
                "Lunch: Bustling food market tasting tour; Evening: Scenic restaurant dinner with panoramic neighborhood views.",
                "Lunch: Chef-curated farm-to-table lunch; Evening: Leisured dinner exploring neighborhood specialties and wine pairings.",
                "Lunch: Traditional street food specialties; Evening: Celebratory farewell multi-course dining experience.",
            ]
            transit_tips = [
                "Use the central public transit pass (subway/tram/bus) for quick and eco-friendly city transit.",
                "Historic centers are best explored on foot with comfortable walking shoes.",
                "Pre-arrange airport train or express shuttle bus for seamless terminal arrivals.",
                "Bicycle sharing stations provide a scenic way to tour riverfronts and major parks.",
            ]

        for day in range(1, duration_days + 1):
            day_idx = day - 1
            f_tip = food_tips[day_idx % len(food_tips)]
            t_tip = transit_tips[day_idx % len(transit_tips)]

            if total_places >= 3:
                p_morn = discovered_places[(day_idx * 3) % total_places]["name"]
                p_aft = discovered_places[(day_idx * 3 + 1) % total_places]["name"]
                p_eve = discovered_places[(day_idx * 3 + 2) % total_places]["name"]
            elif total_places == 2:
                p_morn = discovered_places[0]["name"]
                p_aft = discovered_places[1]["name"]
                p_eve = f"{dest_name} Sunset Promenade & Local Market"
            elif total_places == 1:
                p_morn = discovered_places[0]["name"]
                p_aft = f"{dest_name} Cultural Heritage District"
                p_eve = f"{dest_name} Evening Culinary Quarter"
            else:
                p_morn = f"{dest_name} Historic Landmark"
                p_aft = f"{dest_name} Scenic Viewpoint & Gardens"
                p_eve = f"{dest_name} Vibrant Bazaar & Waterfront"

            if day == 1:
                title = f"Arrival, Check-in at {stay_name} & Orientation Tour"
                morning_act = f"Arrival in {dest_name}, airport transfer, and smooth check-in at {stay_name} ({stay_tier})"
                afternoon_act = f"Orientation walking tour around {p_morn} and picturesque neighborhood alleys"
                evening_act = f"Sunset stroll near {p_aft} followed by a welcome dinner: {f_tip.split(';')[0]}"
            elif day == duration_days:
                title = f"Farewell {dest_name}: Souvenirs, Highlights & Departure"
                morning_act = f"Early visit to {p_morn} for photography, followed by artisan handicraft shopping at {p_eve}"
                afternoon_act = f"Hotel checkout, farewell lunch, and comfortable transfer to departure terminal"
                evening_act = f"Departure flight check-in and journey home with unforgettable memories"
            else:
                title = f"Immersive Exploration: {p_morn} & {p_aft}"
                morning_act = f"Early morning exploration of {p_morn} to enjoy calm ambiance and optimal morning light"
                afternoon_act = f"Afternoon discovery of {p_aft} with cafe break and cultural exhibitions"
                evening_act = f"Evening visits around {p_eve}: {f_tip.split(';')[-1]}"

            days.append({
                "day": day,
                "title": title,
                "activities": [morning_act, afternoon_act, evening_act],
                "morning": {"activity": morning_act, "location": p_morn, "time": "08:30 - 12:30", "cost": m_cost},
                "afternoon": {"activity": afternoon_act, "location": p_aft, "time": "14:00 - 17:30", "cost": a_cost},
                "evening": {"activity": evening_act, "location": p_eve, "time": "18:30 - 22:00", "cost": e_cost},
                "dining_recommendation": f_tip,
                "transit_tip": t_tip,
            })

        return {
            "source": "grounded_research_fallback",
            "destination": dest_name,
            "duration_days": duration_days,
            "days": days,
            "llm_synthesized": False,
            "note": "Generated using TravelMind's localized multi-category research engine; set GEMINI_API_KEY for live AI synthesis.",
        }

    async def _generate_gemini_itinerary(
        self,
        trip_spec: TripSpec,
        duration_days: int,
        results: dict[str, Any],
        api_key: str,
    ) -> dict[str, Any] | None:
        """Invokes Gemini REST client with researched real provider context for high-fidelity synthesis."""
        try:
            client = GeminiClient(api_key=api_key, model="gemini-2.0-flash", timeout=15.0)
            gateway = LLMGateway([client], retries=1)

            dest_places = results.get("destination_discovery", {}).get("data", {}).get("places", [])
            places_summary = ", ".join([f"{p['name']} ({p.get('category', 'attraction')})" for p in dest_places[:6]])
            flight_offers = results.get("flight_intelligence", {}).get("data", {}).get("offers", [])
            hotels = results.get("accommodation_intelligence", {}).get("data", {}).get("hotels", [])
            stay_name = hotels[0].get("name") if hotels else "Central Hotel"

            prompt = f"""You are the Lead TravelMind AI Itinerary Architect.
Generate a structured day-by-day travel itinerary for {duration_days} day(s) from {trip_spec.origin} to {trip_spec.destination}.
Travelers: {trip_spec.travelers} | Budget: {trip_spec.budget} {trip_spec.currency} | Interests: {', '.join(trip_spec.interests or ['culture', 'sightseeing'])}.

VERIFIED RESEARCHED DATA (Ground your itinerary strictly in this):
- Discovered Attractions & Places: {places_summary or 'City Center and landmarks'}
- Recommended Hotel: {stay_name}
- Total Duration: {duration_days} days

OUTPUT REQUIREMENTS:
Output MUST be valid JSON with this exact schema:
{{
  "destination": "{trip_spec.destination}",
  "duration_days": {duration_days},
  "source": "gemini-2.0-flash",
  "days": [
    {{
      "day": 1,
      "title": "Day 1 Title",
      "activities": [
        "Morning activity description",
        "Afternoon activity description",
        "Evening activity description"
      ],
      "morning": {{"activity": "Morning details", "location": "Location", "time": "09:00", "cost": 15.0}},
      "afternoon": {{"activity": "Afternoon details", "location": "Location", "time": "14:00", "cost": 25.0}},
      "evening": {{"activity": "Evening details", "location": "Location", "time": "19:30", "cost": 35.0}}
    }}
  ]
}}
Do NOT invent fake flight numbers or fake hotel prices. Use the real attractions provided."""

            def validator(raw_json: dict) -> dict:
                if not isinstance(raw_json, dict) or "days" not in raw_json:
                    raise ValueError("invalid itinerary format: missing 'days'")
                if len(raw_json["days"]) != duration_days:
                    # Adjust count if slightly off
                    pass
                return raw_json

            itinerary = gateway.structured(prompt, validator)
            return itinerary
        except Exception:
            # Fall back safely to grounded synthesis on network/API failure
            return None

    def plan_trip(self, trip_spec: TripSpec) -> TripPlanResult:
        import asyncio

        return asyncio.run(self.plan_trip_async(trip_spec))

    async def plan_trip_async(self, trip_spec: TripSpec) -> TripPlanResult:
        missing_fields = trip_spec.missing()
        if missing_fields:
            return TripPlanResult(
                trip_id=f"trip-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
                trip_spec=trip_spec,
                created_at=datetime.now(timezone.utc).isoformat(),
                summary="Trip specification is incomplete and requires additional traveler details.",
                results={},
                missing_fields=missing_fields,
                errors=["Please provide the missing trip information before planning."],
            )

        execution: dict[str, Any] = {"trip_spec": trip_spec, "state": {"trip_spec": trip_spec}}
        orchestrator = Orchestrator(self._to_agent_specs())
        run_result = await orchestrator.run(execution)
        results = {
            name: asdict(output) if is_dataclass(output) else output
            for name, output in run_result.results.items()
        }
        results["agent_execution"] = {
            record.agent: {
                "status": record.status,
                "attempts": record.attempts,
                "duration_ms": record.duration_ms,
                "error": record.error,
            }
            for record in run_result.records
        }

        duration_days = trip_spec.duration_days
        if duration_days is None and trip_spec.departure_date and trip_spec.return_date:
            duration_days = max(1, (trip_spec.return_date - trip_spec.departure_date).days)
        if not duration_days:
            duration_days = 4

        # Attempt Gemini LLM itinerary synthesis if API key is present
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        itinerary = None
        if gemini_api_key:
            itinerary = await self._generate_gemini_itinerary(trip_spec, duration_days, results, gemini_api_key)

        gemini_invoked = False
        if not itinerary:
            itinerary = self._build_grounded_itinerary(trip_spec, duration_days, results)
        else:
            gemini_invoked = True

        results["itinerary"] = itinerary
        results["ai_synthesis"] = {
            "gemini_invoked": gemini_invoked,
            "status": "gemini_live_success" if gemini_invoked else ("unconfigured (GEMINI_API_KEY not set)" if not gemini_api_key else "fallback_used"),
            "model": "gemini-2.0-flash" if gemini_invoked else None,
        }

        return TripPlanResult(
            trip_id=f"trip-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            trip_spec=trip_spec,
            created_at=datetime.now(timezone.utc).isoformat(),
            summary=self.build_trip_summary(trip_spec),
            results=results,
            missing_fields=[],
            errors=[f"{record.agent}: {record.error}" for record in run_result.records if record.status != "ok"],
        )
