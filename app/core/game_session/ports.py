"""Puertos que el game_engine requiere de la infraestructura (ADR-04 / ADR-05).

El núcleo define los contratos; ``app.infrastructure.persistence`` los
implementa con Redis y PostgreSQL. Así el núcleo nunca importa redis ni
sqlalchemy (contrato 1 de .importlinter).
"""
from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Any, Protocol


class GameStateStore(Protocol):
    """GameStateRepositoryComponent — estado vivo de la sala (Redis)."""

    def load(self, game_id: str) -> dict[str, Any] | None: ...

    def save(self, game_id: str, snapshot: dict[str, Any]) -> None: ...

    def lock(self, game_id: str) -> AbstractContextManager[None]:
        """Cerrojo exclusivo de la partida (SET NX). Lanza ConcurrencyError si está tomado."""
        ...

    def append_play(self, game_id: str, play: dict[str, Any]) -> None:
        """Bandeja de salida (Outbox): jugadas pendientes de volcar a PostgreSQL."""
        ...

    def pending_plays(self, game_id: str) -> list[dict[str, Any]]: ...

    def clear_plays(self, game_id: str, count: int) -> None: ...

    def active_games(self) -> list[str]: ...

    def deactivate(self, game_id: str) -> None: ...


class HistoryStore(Protocol):
    """Fuente de verdad a largo plazo (PostgreSQL en 3FN)."""

    def create_session(self, snapshot: dict[str, Any], plays: list[dict[str, Any]]) -> None: ...

    def settle_round(
        self,
        game_id: str,
        round_number: int,
        closer_seat: str,
        penalties: dict[str, int],
        totals: dict[str, int],
        plays: list[dict[str, Any]],
        snapshot: dict[str, Any],
        next_round: int | None,
    ) -> None:
        """Transacción ACID única: ronda + scores + acumulados + jugadas + snapshot.

        Lanza ConcurrencyError si la ronda ya no está abierta (mitigación R6).
        """
        ...

    def latest_snapshot(self, game_id: str) -> dict[str, Any] | None: ...

    def find_by_pin(self, pin: str) -> str | None: ...

    def plays(self, game_id: str) -> list[dict[str, Any]]: ...

    def list_sessions(self, limit: int = 20) -> list[dict[str, Any]]: ...


class Notifier(Protocol):
    """SessionNotificationComponent (WebSocket Gateway)."""

    def publish(self, game_id: str, event: str, version: int) -> None: ...


class NullNotifier:
    def publish(self, game_id: str, event: str, version: int) -> None:
        return None
