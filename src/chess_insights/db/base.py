"""SQLAlchemy declarative base.

Domain ORM models (introduced in a later phase) will subclass ``Base``. No
models are defined here yet.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
