from __future__ import annotations

try:
    from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String, Text
    from sqlalchemy.orm import relationship
except ImportError:
    Column = None
    Float = None
    ForeignKey = None
    Integer = None
    String = None
    Text = None
    Boolean = None
    relationship = None

from .base import Base


if Column is not None:
    class Subscription(Base):  # type: ignore[misc, valid-type]
        __tablename__ = "subscriptions"

        id = Column(String, primary_key=True)
        user_id = Column(String, ForeignKey("users.id"), nullable=False)
        tier = Column(String, nullable=False, default="free")  # free, pro, enterprise
        status = Column(String, nullable=False, default="active")  # active, canceled, past_due
        current_period_end = Column(String, nullable=True)
        cancel_at_period_end = Column(Boolean, default=False)
        stripe_customer_id = Column(String, nullable=True)
        stripe_subscription_id = Column(String, nullable=True)
        created_at = Column(String, nullable=False)

    class Payment(Base):  # type: ignore[misc, valid-type]
        __tablename__ = "payments"

        id = Column(String, primary_key=True)
        user_id = Column(String, ForeignKey("users.id"), nullable=False)
        trip_id = Column(String, ForeignKey("trips.id"), nullable=True)
        amount = Column(Float, nullable=False)
        currency = Column(String, default="USD")
        status = Column(String, default="succeeded")  # succeeded, pending, failed
        provider = Column(String, default="stripe")
        provider_payment_id = Column(String, nullable=True)
        created_at = Column(String, nullable=False)

    class Notification(Base):  # type: ignore[misc, valid-type]
        __tablename__ = "notifications"

        id = Column(String, primary_key=True)
        user_id = Column(String, ForeignKey("users.id"), nullable=False)
        trip_id = Column(String, ForeignKey("trips.id"), nullable=True)
        type = Column(String, nullable=False)  # departure_reminder, price_alert, packing_tip, system
        title = Column(String, nullable=False)
        message = Column(Text, nullable=False)
        status = Column(String, default="unread")  # unread, read, archived
        sent_at = Column(String, nullable=True)
        created_at = Column(String, nullable=False)

    class ProviderSearchRecord(Base):  # type: ignore[misc, valid-type]
        __tablename__ = "provider_search_records"

        id = Column(String, primary_key=True)
        provider = Column(String, nullable=False)
        query = Column(Text, nullable=False)
        status = Column(String, nullable=False)
        response_data = Column(Text, nullable=True)
        created_at = Column(String, nullable=False)

    class AgentExecutionLog(Base):  # type: ignore[misc, valid-type]
        __tablename__ = "agent_execution_logs"

        id = Column(String, primary_key=True)
        trip_id = Column(String, ForeignKey("trips.id"), nullable=True)
        agent_name = Column(String, nullable=False)
        status = Column(String, nullable=False)
        duration_ms = Column(Integer, default=0)
        error = Column(Text, nullable=True)
        created_at = Column(String, nullable=False)

else:
    class Subscription:  # type: ignore[no-redef]
        pass

    class Payment:  # type: ignore[no-redef]
        pass

    class Notification:  # type: ignore[no-redef]
        pass

    class ProviderSearchRecord:  # type: ignore[no-redef]
        pass

    class AgentExecutionLog:  # type: ignore[no-redef]
        pass
