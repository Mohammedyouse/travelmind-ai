from __future__ import annotations

from typing import Any

from ..core.types import TripSpec
from .base import TravelAgent


def _extract_data(agent_output: Any) -> dict[str, Any]:
    if agent_output is None:
        return {}
    if hasattr(agent_output, "data") and isinstance(agent_output.data, dict):
        return agent_output.data
    if isinstance(agent_output, dict):
        return agent_output.get("data", agent_output)
    return {}


class PersonalizationRecommendationAgent(TravelAgent):
    name = "personalization_recommendation"
    description = "Creates personalized recommendations using explainable ranking based on traveler profile and interests."
    requires = ("trip_spec",)

    def run(self, context: dict[str, Any]):
        trip_spec = context.get("trip_spec") or context.get("state", {}).get("trip_spec")
        if trip_spec is None:
            return self._build_output(
                status="needs_input",
                summary="No profile details available for personalization.",
                missing_fields=["trip_spec"],
            )

        if not isinstance(trip_spec, TripSpec):
            trip_spec = TripSpec.from_dict(trip_spec)

        interests = trip_spec.interests or ["food", "culture", "relaxation"]
        traveler_style = "value-seeking" if (trip_spec.budget or 0) < 2500 else "balanced"

        # Read discovered places from destination_discovery if present in context
        results = context.get("results", {})
        dest_data = _extract_data(results.get("destination_discovery"))
        places = dest_data.get("places", [])

        ranked_places = []
        for place in places:
            name = place.get("name", "")
            cat = place.get("category", "")
            rating = place.get("rating", 4.5)
            # Match place category with user interests
            match_score = 0.5
            for interest in interests:
                if interest.lower() in cat.lower() or interest.lower() in name.lower():
                    match_score += 0.3
            final_score = round(min(1.0, (rating / 5.0) * 0.5 + match_score * 0.5), 3)
            ranked_places.append({
                "name": name,
                "category": cat,
                "rating": rating,
                "fit_score": final_score,
                "address": place.get("address", ""),
            })

        ranked_places.sort(key=lambda x: x["fit_score"], reverse=True)

        recommendations = [
            f"Prioritize {interest} experiences that align with the traveler’s {traveler_style} style."
            for interest in interests
        ]
        if ranked_places:
            top_spot = ranked_places[0]["name"]
            recommendations.append(f"Top tailored recommendation for your interests: {top_spot}.")
        recommendations.append("Favor local neighborhoods and strategic transport to maximize time and minimize fatigue.")

        return self._build_output(
            status="ok",
            summary=f"Personalized recommendations generated for travelers with a {traveler_style} profile.",
            data={
                "traveler_style": traveler_style,
                "interests": interests,
                "recommendation_count": len(recommendations),
                "ranked_highlights": ranked_places[:5],
            },
            recommendations=recommendations,
        )
