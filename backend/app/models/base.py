from __future__ import annotations

try:
    from sqlalchemy.orm import declarative_base
except ImportError:  # pragma: no cover
    declarative_base = None


if declarative_base is not None:
    Base = declarative_base()
else:  # pragma: no cover
    class Base:  # type: ignore[no-redef]
        pass
