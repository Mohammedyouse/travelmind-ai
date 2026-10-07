from __future__ import annotations

try:
    from sqlalchemy import Column, Float, ForeignKey, Integer, String, Text
    from sqlalchemy.orm import relationship
except ImportError:  # pragma: no cover
    Column = None
    Float = None
    ForeignKey = None
    Integer = None
    String = None
    Text = None
    relationship = None

from .base import Base


if Column is not None:
    class Trip(Base):  # type: ignore[misc, valid-type]
        __tablename__ = "trips"

        id = Column(String, primary_key=True)
        user_id = Column(String, ForeignKey("users.id"), nullable=False)
        origin = Column(String, nullable=True)
        destination = Column(String, nullable=True)
        departure_date = Column(String, nullable=True)
        return_date = Column(String, nullable=True)
        duration_days = Column(Integer, nullable=True)
        travelers = Column(Integer, nullable=False, default=1)
        budget = Column(Float, nullable=True)
        currency = Column(String, nullable=False, default="USD")
        status = Column(String, nullable=False, default="draft")
        summary = Column(Text, nullable=True)
        preferences = Column(Text, nullable=False, default="{}")
        plan_results = Column(Text, nullable=False, default="{}")
        created_at = Column(String, nullable=False)

        owner = relationship("User", back_populates="trips")
        items = relationship("ItineraryItem", back_populates="trip")

    class ItineraryItem(Base):  # type: ignore[misc, valid-type]
        __tablename__ = "itinerary_items"

        id = Column(String, primary_key=True)
        trip_id = Column(String, ForeignKey("trips.id"), nullable=False)
        day = Column(Integer, nullable=False)
        title = Column(String, nullable=False)
        description = Column(Text, nullable=True)
        cost = Column(Float, default=0.0)
        created_at = Column(String, nullable=False)

        trip = relationship("Trip", back_populates="items")

    class Conversation(Base):  # type: ignore[misc, valid-type]
        __tablename__ = "conversations"

        id = Column(String, primary_key=True)
        trip_id = Column(String, ForeignKey("trips.id"), nullable=True)
        user_id = Column(String, ForeignKey("users.id"), nullable=False)
        role = Column(String, nullable=False)
        content = Column(Text, nullable=False)
        created_at = Column(String, nullable=False)

    class BudgetSnapshot(Base):  # type: ignore[misc, valid-type]
        __tablename__ = "budget_snapshots"

        id = Column(String, primary_key=True)
        trip_id = Column(String, ForeignKey("trips.id"), nullable=False)
        currency = Column(String, default="USD")
        total = Column(Float, default=0.0)
        contingency = Column(Float, default=0.0)

    class Preference(Base):  # type: ignore[misc, valid-type]
        __tablename__ = "preferences"

        id = Column(String, primary_key=True)
        user_id = Column(String, ForeignKey("users.id"), nullable=False)
        key = Column(String, nullable=False)
        value = Column(String, nullable=False)
        created_at = Column(String, nullable=False)
else:  # pragma: no cover
    class Trip:  # type: ignore[no-redef]
        pass

    class ItineraryItem:  # type: ignore[no-redef]
        pass

    class BudgetSnapshot:  # type: ignore[no-redef]
        pass

    class Preference:  # type: ignore[no-redef]
        pass

    class Conversation:  # type: ignore[no-redef]
        pass
