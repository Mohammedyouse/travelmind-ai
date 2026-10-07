"""TravelMind AI backend package."""

__all__ = ["build_agent_registry", "TripService"]


def build_agent_registry():
    from .agents import build_agent_registry as _build_agent_registry
    return _build_agent_registry()


def TripService():
    from .services.trip_service import TripService as _TripService
    return _TripService()
