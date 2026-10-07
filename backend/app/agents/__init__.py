"""TravelMind AI agent registry and shared interfaces."""

from .base import AgentOutput, TravelAgent
from .travel_concierge import TravelConciergeAgent
from .flight_intelligence import FlightIntelligenceAgent
from .accommodation_intelligence import AccommodationIntelligenceAgent
from .destination_discovery import DestinationDiscoveryAgent
from .transportation_route import TransportationRouteAgent
from .budget_intelligence import BudgetIntelligenceAgent
from .personalization_recommendation import PersonalizationRecommendationAgent
from .travel_support import TravelSupportAgent


__all__ = [
    "AgentOutput",
    "TravelAgent",
    "TravelConciergeAgent",
    "FlightIntelligenceAgent",
    "AccommodationIntelligenceAgent",
    "DestinationDiscoveryAgent",
    "TransportationRouteAgent",
    "BudgetIntelligenceAgent",
    "PersonalizationRecommendationAgent",
    "TravelSupportAgent",
    "build_agent_registry",
]


def build_agent_registry() -> dict[str, TravelAgent]:
    return {
        agent.name: agent
        for agent in (
            TravelConciergeAgent(),
            FlightIntelligenceAgent(),
            AccommodationIntelligenceAgent(),
            DestinationDiscoveryAgent(),
            TransportationRouteAgent(),
            BudgetIntelligenceAgent(),
            PersonalizationRecommendationAgent(),
            TravelSupportAgent(),
        )
    }
