from __future__ import annotations

try:
    from sqlalchemy import Boolean, Column, String
    from sqlalchemy.orm import relationship
except ImportError:  # pragma: no cover
    Column = None
    String = None
    Boolean = None
    relationship = None

from .base import Base


if Column is not None:
    class User(Base):  # type: ignore[misc, valid-type]
        __tablename__ = "users"

        id = Column(String, primary_key=True)
        email = Column(String, unique=True, nullable=False)
        full_name = Column(String, nullable=False)
        password_hash = Column(String, nullable=False)
        is_active = Column(Boolean, nullable=False, default=True, server_default="true")
        role = Column(String, default="traveler")
        created_at = Column(String, nullable=False)

        trips = relationship("Trip", back_populates="owner")
else:  # pragma: no cover
    class User:  # type: ignore[no-redef]
        pass
