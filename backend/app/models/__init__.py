"""Persistence models for TravelMind AI."""

try:
    from .base import Base
    from .user import User
    from .trip import Trip, ItineraryItem, BudgetSnapshot, Preference, Conversation
    from .saas import Subscription, Payment, Notification, ProviderSearchRecord, AgentExecutionLog
except ImportError:  # pragma: no cover
    Base = None
    User = None
    Trip = None
    ItineraryItem = None
    BudgetSnapshot = None
    Preference = None
    Conversation = None
    Subscription = None
    Payment = None
    Notification = None
    ProviderSearchRecord = None
    AgentExecutionLog = None

__all__ = [
    "Base",
    "User",
    "Trip",
    "ItineraryItem",
    "BudgetSnapshot",
    "Preference",
    "Conversation",
    "Subscription",
    "Payment",
    "Notification",
    "ProviderSearchRecord",
    "AgentExecutionLog",
]
