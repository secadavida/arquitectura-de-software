"""Modelo relacional (PostgreSQL, 3FN)."""
from app.infrastructure.models import game_session, user  # noqa: F401 - registra las tablas
from app.infrastructure.models.base import metadata

__all__ = ["metadata"]
