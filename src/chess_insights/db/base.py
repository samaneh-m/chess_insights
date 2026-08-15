"""SQLAlchemy declarative base and small shared column helpers.

ORM models live under ``chess_insights.db.models`` and subclass ``Base``.
"""

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, MappedColumn, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


def timestamp_column(*, onupdate: bool = False, nullable: bool = False) -> MappedColumn[datetime]:
    """A timezone-aware ``DateTime`` column defaulting to the current time.

    Used for ``created_at``/``updated_at`` style columns so every model
    gets the same UTC-aware behavior instead of ad-hoc datetime defaults.
    """
    return mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now() if onupdate else None,
        nullable=nullable,
    )


def enum_column(
    enum_cls: type[enum.Enum], *, name: str, nullable: bool = False
) -> MappedColumn[Any]:
    """A ``VARCHAR + CHECK`` column storing an enum's string ``.value``.

    ``native_enum=False`` deliberately avoids PostgreSQL native ``ENUM``
    types: adding/renaming a value would otherwise require ``ALTER TYPE``
    migrations, which is unnecessary complexity for this project's scope.
    """
    return mapped_column(
        SAEnum(
            enum_cls,
            name=name,
            native_enum=False,
            validate_strings=True,
            values_callable=lambda cls: [member.value for member in cls],
        ),
        nullable=nullable,
    )
