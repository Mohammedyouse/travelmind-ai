from __future__ import annotations

import os
from typing import Any

from ..core.types import TripSpec
from ..integrations.places import build_places_provider
from .base import TravelAgent


class DestinationDiscoveryAgent(TravelAgent):
    name = "destination_discovery"
    description = "Discovers real attractions, culinary spots, and cultural landmarks aligned with traveler interests."
    requires = ("trip_spec",)

    def run(self, context: dict[str, Any]):
        trip_spec = context.get("trip_spec") or context.get("state", {}).get("trip_spec")
        if trip_spec is None:
            return self._build_output(
                status="needs_input",
                summary="No destination has been selected yet.",
                missing_fields=["trip_spec"],
            )

        if not isinstance(trip_spec, TripSpec):
            trip_spec = TripSpec.from_dict(trip_spec)

        if not trip_spec.destination:
            return self._build_output(
                status="needs_input",
                summary="Destination discovery requires a destination.",
                missing_fields=["destination"],
            )

        interests = trip_spec.interests or ["culture", "food", "nature"]
        places_provider = build_places_provider()
        places_res = places_provider.search_places(trip_spec.destination, limit=18)

        raw_places = places_res.data.get("places", []) if places_res.ok and places_res.data else []
        places = [
            {
                **p,
                "latitude": p.get("lat") if p.get("latitude") is None else p.get("latitude"),
                "longitude": p.get("lon") if p.get("longitude") is None else p.get("longitude"),
                "lat": p.get("lat") if p.get("lat") is not None else p.get("latitude"),
                "lon": p.get("lon") if p.get("lon") is not None else p.get("longitude"),
            }
            for p in raw_places
        ]
        if places:
            highlights = [f"{p['name']} ({p.get('category', 'attraction').replace('_', ' ').title()})" for p in places[:8]]
        else:
            highlights = [
                f"Cultural landmarks around {trip_spec.destination}",
                "Local food and market experiences",
                "Scenic neighborhoods and iconic viewpoints",
            ]

        coords = places_res.data.get("coordinates") if places_res.data else None

        discovery = {
            "destination": trip_spec.destination,
            "interests": interests,
            "highlights": highlights,
            "best_for": sorted(set(interests)),
            "places": places,
            "coordinates": coords,
            "source": places_res.data.get("source", "verified_destination_places") if places_res.ok else "unconfigured",
        }

        return self._build_output(
            status="ok",
            summary=f"Destination discovery for {trip_spec.destination} completed: curated {len(places)} verified places and iconic attractions across heritage, nature, and food.",
            data={"destination": discovery, "places": places, "coordinates": coords},
            recommendations=[
                "Prioritize top-rated heritage and cultural landmarks during cooler morning slots.",
                "Visit scenic viewpoints and waterfronts during sunset hours.",
                "Explore bustling local markets and food lanes in the evening for authentic dining.",
            ],
        )
